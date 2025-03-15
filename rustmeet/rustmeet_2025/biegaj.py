from __future__ import annotations

import asyncio
import bisect
import json
from collections import defaultdict
from datetime import datetime
from functools import partial
from itertools import starmap
from operator import attrgetter
from pathlib import Path
from typing import NamedTuple

import aiomqtt
import logfire
import rich
import typer
from pydantic import TypeAdapter

from consumer.main import DatabaseEngine, loop_consume_messages
from consumer.questions import Question, read_questions_from_file
from consumer.settings import Settings, configure_logfire, get_db
from consumer.stats import DeviceStatistics, Statistics, stats_from_db, update_stats
from consumer.utils import should_skip

QUESTIONS_FILE = Path("rustmeet/rustmeet_2025/questions.yml")
LEADERBOARD_FILE = Path("leaderboard.json")
EVENTS_FILE = Path("events.txt")

cli = typer.Typer()


class LeaderboardItem(NamedTuple):
    device_id: str
    device_statistics: DeviceStatistics

    def __str__(self) -> str:
        stats = self.device_statistics
        return (
            f"{self.device_id} (correct: {stats.total_correct_answers}, "
            f"total answers: {stats.total_answers})"
        )


def get_leaderboard(statistics: Statistics) -> list[LeaderboardItem]:
    leaderboard: list[LeaderboardItem] = []
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

    event = {
        "captured_at": datetime.now().isoformat(),  # noqa: DTZ005
        "caused_by": (question.model_dump(), answer.model_dump()),
        "state": TypeAdapter(Statistics).dump_python(statistics),  # type: ignore[arg-type]
    }

    rich.print(event)

    with EVENTS_FILE.open(mode="a") as events_file:  # noqa: ASYNC230
        await asyncio.to_thread(
            events_file.write,
            json.dumps(event, indent=2, ensure_ascii=False) + "\n",
        )
        logfire.info("Wrote event to {events_file}", events_file=EVENTS_FILE)


async def main(topic: str = "answer", *, questions: dict[str, Question]) -> None:
    statistics: Statistics = defaultdict(partial(DeviceStatistics, questions))
    await loop_consume_messages(
        callback=partial(on_message, statistics, topic, questions=questions),
        settings=Settings(),
        topics=[topic],
    )


@cli.command("listen")
def command_listen() -> None:
    configure_logfire()
    questions = read_questions_from_file(questions_file=QUESTIONS_FILE)
    asyncio.run(main(questions=questions))


async def leaderboard_from_db(
    settings: Settings,
    questions: dict[str, Question],
) -> list[LeaderboardItem]:
    async with get_db(settings.db_path) as db:
        stats = await stats_from_db(db, questions)
        await asyncio.to_thread(
            LEADERBOARD_FILE.write_bytes,
            TypeAdapter(Statistics).dump_json(stats, indent=2),  # type: ignore[arg-type]
        )
        logfire.info(
            "Wrote leaderboard to {leaderboard_file}",
            events_file=LEADERBOARD_FILE,
        )
        return get_leaderboard(stats)


@cli.command("leaderboard")
def command_leaderboard() -> None:
    configure_logfire()
    settings = Settings()
    questions = read_questions_from_file(questions_file=QUESTIONS_FILE)
    leaderboard = asyncio.run(leaderboard_from_db(settings, questions))
    rich.print(leaderboard)


if __name__ == "__main__":
    cli()
