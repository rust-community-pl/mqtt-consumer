from __future__ import annotations

import functools
import os
import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import aiomqtt
import dotenv
import logfire
from pydantic import BeforeValidator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import Field

if TYPE_CHECKING:
    from _typeshed import StrPath

SUBSCRIBER_ENV_FILE = os.getenv("SUBSCRIBER_ENV_FILE") or ".env"


@functools.lru_cache(1)
def configure_logfire() -> None:
    dotenv.load_dotenv(SUBSCRIBER_ENV_FILE)
    logfire.configure(
        console=logfire.ConsoleOptions(show_project_link=False),
        inspect_arguments=False,
    )


class MQTTCredentials(
    BaseSettings,
    env_prefix="SUBSCRIBER_MQTT_",
    env_file=SUBSCRIBER_ENV_FILE,
):
    hostname: str
    port: int
    username: str
    password: SecretStr = Field(repr=False)
    use_tls: bool

    model_config = SettingsConfigDict(extra="ignore")


def sanitize_db_path(db_path: StrPath | Literal[":memory:"]) -> str:
    if db_path != ":memory:":
        return f"/{Path(db_path).absolute()!s}"
    return db_path


type DBPath = Annotated[str, BeforeValidator(sanitize_db_path)]


class Settings(
    BaseSettings,
    env_prefix="SUBSCRIBER_",
    env_file=SUBSCRIBER_ENV_FILE,
):
    db_path: DBPath = "consumer.db"
    mqtt: Annotated[MQTTCredentials, Field(default_factory=MQTTCredentials)]

    model_config = SettingsConfigDict(extra="ignore")


def get_mqtt_client(mqtt_credentials: MQTTCredentials) -> aiomqtt.Client:
    return aiomqtt.Client(
        hostname=mqtt_credentials.hostname,
        port=mqtt_credentials.port,
        username=mqtt_credentials.username,
        password=mqtt_credentials.password.get_secret_value(),
        tls_context=ssl.create_default_context() if mqtt_credentials.use_tls else None,
    )


@asynccontextmanager
async def get_db(db_path: str) -> AsyncGenerator[AsyncEngine]:
    db = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        yield db
    finally:
        await db.dispose()
