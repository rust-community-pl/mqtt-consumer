import os
import ssl
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncGenerator

import aiomqtt
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import Field

SUBSCRIBER_ENV_FILE = os.getenv("SUBSCRIBER_ENV_FILE") or ".env"


class MQTTCredentials(
    BaseSettings,
    env_prefix="SUBSCRIBER_MQTT_",
    env_file=SUBSCRIBER_ENV_FILE,
):
    hostname: str
    port: int
    username: str
    password: SecretStr
    use_tls: bool


class Settings(
    BaseSettings,
    env_prefix="SUBSCRIBER_",
    env_file=SUBSCRIBER_ENV_FILE,
):
    db_path: Annotated[Path, Field(default="consumer.db")]
    mqtt: Annotated[MQTTCredentials, Field(default_factory=MQTTCredentials)]


def get_mqtt_client(mqtt_credentials: MQTTCredentials) -> aiomqtt.Client:
    return aiomqtt.Client(
        hostname=mqtt_credentials.hostname,
        port=mqtt_credentials.port,
        username=mqtt_credentials.username,
        password=mqtt_credentials.password.get_secret_value(),
        tls_context=ssl.create_default_context() if mqtt_credentials.use_tls else None,
    )


@asynccontextmanager
async def get_db(db_path: Path) -> AsyncGenerator[AsyncEngine]:
    db = create_async_engine(f"sqlite+aiosqlite:////{db_path.absolute()}")
    try:
        yield db
    finally:
        await db.dispose()
