from __future__ import annotations

import asyncio
import bisect
from collections import defaultdict
from functools import partial
from itertools import starmap
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import aiomqtt
from pydantic import TypeAdapter

from consumer.main import DatabaseEngine, loop_consume_messages
from consumer.questions import Question, read_questions_from_file
from consumer.settings import Settings, configure_logfire
from consumer.stats import DeviceStatistics, Statistics, update_stats
from consumer.utils import should_skip

if TYPE_CHECKING:
    pass

QUESTIONS_FILE = Path("rustmeet/rustmeet_2025/questions.yml")

COUNTER_PATTERN = (
    r"<!--question:({question_id})-->(?P<answers>\d*)<!--question:({question_id})-->"
)
LEADERBOARD_PATTERN = r"<!--leaderboard-->(.*)<!--leaderboard-->"


class LeaderboardItem(NamedTuple):
    device_id: str
    device_statistics: DeviceStatistics

    def __str__(self) -> str:
        stats = self.device_statistics
        return (
            f"{self.device_id} (correct: {stats.total_correct_answers}, "
            f"total answers: {stats.total_answers})"
        )


def get_leaderboard(statistics: Statistics) -> str:
    leaderboard = []
    for item in starmap(LeaderboardItem, statistics.items()):
        bisect.insort(
            leaderboard, item, key=attrgetter("device_statistics.total_correct_answers")
        )
    return leaderboard


async def on_message(
    statistics: Statistics,
    expected_topic: str,
    message: aiomqtt.Message,
    db: DatabaseEngine,
    *,
    questions: dict[str, Question],
) -> None:
    if should_skip(message, expected_topic):
        return

    updated = await update_stats(
        statistics,
        message,
        db,
        questions=questions,
    )
    if updated is None:
        return

    question, answer = updated
    await asyncio.to_thread(
        Path(f"stats/db-stats-{question.id}-from-{answer.device_id}.json").write_bytes,
        TypeAdapter(Statistics).dump_json(statistics, indent=2),
    )


async def main(topic: str = "answer", *, questions: dict[str, Question]) -> None:
    statistics = defaultdict(partial(DeviceStatistics, questions))
    await loop_consume_messages(
        callback=partial(on_message, statistics, topic, questions=questions),
        settings=Settings(),
        topics=[topic],
    )


if __name__ == "__main__":
    configure_logfire()
    questions = read_questions_from_file(questions_file=QUESTIONS_FILE)
    asyncio.run(main(questions=questions))
