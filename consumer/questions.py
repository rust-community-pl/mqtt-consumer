from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Self

import yaml
from pydantic import BaseModel, TypeAdapter, model_validator

from consumer.answers import Choices
from consumer.utils import StrippedStr

if TYPE_CHECKING:
    from _typeshed import StrPath

type Questions = dict[str, Question]


class Answers(BaseModel):
    choices: dict[Choices, StrippedStr]
    correct: tuple[Choices, StrippedStr]
    comment: StrippedStr | None = None

    @model_validator(mode="after")
    def check_consistent(self) -> Self:
        correct_choice, correct_answer = self.correct

        choosed_answer = self.choices.get(correct_choice)
        if choosed_answer is None:
            msg = (
                f"In the `correct` field, the referenced answer ({correct_choice}) "
                f"cannot be found in the possible `choices` {self.choices}"
            )
            raise ValueError(msg)

        if choosed_answer != correct_answer:
            msg = (
                f"Failed to validate the selected answer {correct_choice} as one "
                f"of legal choices {self.choices}.\n"
                f"{choosed_answer!r} != {correct_answer!r}"
            )
            raise ValueError(msg)
        return self


class Question(BaseModel):
    content: StrippedStr
    id: StrippedStr
    answers: Answers


def read_questions_from_file(questions_file: StrPath) -> Questions:
    questions_file_path = Path(questions_file)
    file_contents = yaml.safe_load(questions_file_path.read_text())
    questions = TypeAdapter(list[Question]).validate_python(file_contents)
    return {question.id: question for question in questions}
