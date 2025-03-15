import os
from collections.abc import AsyncGenerator
from pathlib import Path

import logfire as logfire_lib
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from consumer.answers import Answer
from consumer.settings import (
    SUBSCRIBER_ENV_FILE,
    DBPath,
    MQTTCredentials,
    Settings,
    get_db,
)
from scripts.publish_samples import get_sample_payloads

SUBSCRIBER_TEST_ENV_FILE = os.getenv("SUBSCRIBER_TEST_ENV_FILE") or SUBSCRIBER_ENV_FILE
SAMPLES_FILE = Path("tests/test-samples.txt")


class TestSettings(Settings):
    db_path: DBPath = ":memory:"


class MQTTTestCredentials(
    MQTTCredentials,
    env_prefix="SUBSCRIBER_MQTT_TEST_",
    env_file=SUBSCRIBER_TEST_ENV_FILE,
):
    pass


@pytest.fixture(autouse=True, scope="session")
def logfire() -> logfire_lib.Logfire:
    return logfire_lib.configure(
        console=logfire_lib.ConsoleOptions(show_project_link=False),
        inspect_arguments=False,
        local=True,
        service_name="tests",
    )


@pytest.fixture(autouse=True, scope="session")
def settings() -> Settings:
    return TestSettings(mqtt=MQTTTestCredentials())


@pytest.fixture(autouse=True, scope="session")
def populate_test_db(settings: Settings) -> None:
    if settings.db_path == ":memory:":
        engine = create_engine(f"sqlite:///{settings.db_path}")
        SQLModel.metadata.create_all(engine)


@pytest_asyncio.fixture(autouse=True, loop_scope="function", scope="function")
async def test_db(settings: Settings) -> AsyncGenerator[AsyncSession]:
    async with get_db(settings.db_path) as test_db:
        session = AsyncSession(test_db)
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(scope="session")
def sample_answers() -> list[Answer]:
    return [*map(Answer.from_message, get_sample_payloads(SAMPLES_FILE))]
