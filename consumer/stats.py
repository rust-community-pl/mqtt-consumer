from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Generator
from functools import partial

import aiomqtt
import logfire
from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from consumer.answers import Answer, DeviceID, save_answer
from consumer.main import DatabaseEngine
from consumer.questions import Question, Questions
from consumer.utils import get_message_payload

type Statistics = dict[DeviceID, DeviceStatistics]
STATISTICS_LOCK = asyncio.Lock()


@pydantic_dataclass
class DeviceStatistics:
    questions: Questions = Field(repr=False, exclude=True)
    answers: dict[str, Answer] = Field(default_factory=dict, repr=False)

    def add_answer(self, question: Question, answer: Answer) -> None:
        if question.id != answer.question_id:
            logfire.error(
                "Statistics: Question {question} isn't related to answer {answer}",
                question=question,
                answer=answer,
            )
            return
        existing_answer = self.answers.get(question.id)

        if existing_answer:
            logfire.info(
                "Statistics: Ignoring existing answer {answer} "
                "of device ID {device_id}",
                answer=answer,
            )

        self.answers[question.id] = answer

    @property
    def total_answers(self) -> int:
        return len(self.answers)

    @property
    def total_correct_answers(self) -> int:
        return len(dict(self.get_correct_answers()))

    def get_correct_answers(self) -> Generator[tuple[str, Answer]]:
        for question_id, answer in self.answers.items():
            question = self.questions.get(question_id)
            if question is None:
                logfire.error(
                    "Tried to process answer for {question} but it doesn't "
                    "exist in the question context {questions}",
                    question=question,
                    questions=self.questions,
                )
                continue

            if question_id != answer.question_id:
                # Bad internal path
                continue

            correct_id, _ = question.answers.correct
            if correct_id == answer.choice:
                yield question_id, answer

    def __repr__(self) -> str:
        total_correct_answers = self.total_correct_answers
        total_answers = self.total_answers
        return f"{type(self).__name__}({total_correct_answers=}, {total_answers=})"


async def update_stats(
    statistics: Statistics,
    message: aiomqtt.Message,
    db: DatabaseEngine,
    questions: dict[str, Question],
) -> tuple[Question, Answer] | None:
    payload = get_message_payload(message)
    try:
        answer = Answer.from_message(payload)
    except ValueError:
        logfire.exception(f"Ignoring incorrect payload {payload}", payload=payload)
        return None

    async with STATISTICS_LOCK:
        if await save_answer(answer, db):
            question = questions.get(answer.question_id)
            if question is None:
                logfire.error(
                    "Tried to update statistics with answer {answer}, "
                    "but it points to a question outside of the question context",
                    answer=answer,
                )
                return None

            statistics[answer.device_id].add_answer(question, answer)
            return question, answer

    return None


async def stats_from_db(db: DatabaseEngine, questions: Questions) -> Statistics:
    async with AsyncSession(db) as session:
        all_answers_qs = await session.exec(select(Answer))
        all_answers = all_answers_qs.fetchall()

    statistics: Statistics = defaultdict(partial(DeviceStatistics, questions))
    for answer in all_answers:
        question = questions.get(answer.question_id)
        if question is None:
            logfire.error(
                "Tried to update statistics with answer {answer}, "
                "but it points to a question outside of the question context",
                answer=answer,
            )
            continue
        statistics[answer.device_id].add_answer(question, answer)
    return dict(statistics)
