from __future__ import annotations

from functools import partial
from pathlib import Path
from textwrap import dedent, shorten
from typing import TYPE_CHECKING

from consumer.answers import Choices
from consumer.questions import Question, read_questions_from_file

if TYPE_CHECKING:
    from _typeshed import StrPath

INPUT_FILE = Path("rustmeet/rustmeet_2025/questions.yml")
PRESENTATION_FILE = Path("rustmeet/rustmeet_2025/quiz.md")
PAYLOADS_FILE = Path("rustmeet/rustmeet_2025/question-payloads.txt")


fancy_options: dict[Choices, str] = {
    0: "foo",
    1: "bar",
    2: "biz",
    3: "baz",
}


def question_to_slide(
    question: Question,
    *,
    highlight_correct: bool = False,
) -> str:
    lines = [
        f"# Question {question.id}",
        question.content + "\n",
        "### Answers",
    ]
    for choice_id, choice in question.answers.choices.items():
        include = f"`{fancy_options[choice_id]}` ← {choice}"
        if highlight_correct and question.answers.correct[0] == choice_id:
            include = include.join(("**", "**"))
        lines.append(f"- {include}")
    return "\n".join(lines)


def generate_presentation(
    questions: list[Question],
    output_file: StrPath = PRESENTATION_FILE,
) -> None:
    chunks = [
        dedent("""
        <!--
        theme: default
        paginate: true
        headingDivider: 2
        -->
        """),
        *map(question_to_slide, questions),
        "# Correct answers",
        *map(partial(question_to_slide, highlight_correct=True), questions),
    ]
    Path(output_file).write_text("\n\n".join(chunks))


def question_to_payload(question: Question, sep: str = "|") -> str:
    return sep.join(
        (
            question.id,
            f"Question {shorten(question.id, width=5)}",
            *fancy_options.values(),
        )
    )


def generate_payloads(
    questions: list[Question],
    output_file: StrPath = PAYLOADS_FILE,
) -> None:
    Path(output_file).write_text("\n".join(map(question_to_payload, questions)))


def main(
    questions_file: StrPath = INPUT_FILE,
    presentation_file: StrPath = PRESENTATION_FILE,
    payloads_file: StrPath = PAYLOADS_FILE,
) -> None:
    questions = list(read_questions_from_file(questions_file).values())
    generate_presentation(questions, output_file=presentation_file)
    generate_payloads(questions, output_file=payloads_file)


if __name__ == "__main__":
    main()
