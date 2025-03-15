import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import aiomqtt
import logfire
from sqlalchemy.ext.asyncio import AsyncEngine

from consumer.settings import Settings, get_db, get_mqtt_client
from consumer.utils import get_message_payload

type DatabaseEngine = AsyncEngine
type Callback = Callable[[aiomqtt.Message, AsyncEngine], Coroutine[Any, Any, Any]]


async def consume_message(
    *,
    callback: Callback,
    message: aiomqtt.Message,
    db: AsyncEngine,
    tasks: asyncio.TaskGroup,
) -> None:
    tasks.create_task(callback(message, db))
    logfire.info("Processing {message}", message=get_message_payload(message))
    await asyncio.sleep(0)


async def consume_messages(
    *,
    callback: Callback,
    db: AsyncEngine,
    settings: Settings,
    topics: list[str],
) -> None:
    try:
        async with get_mqtt_client(settings.mqtt) as client:
            logfire.info("Connected to {mqtt}", mqtt=settings.mqtt)
            for topic in topics:
                await client.subscribe(topic)
                logfire.info("Subscribed to `{topic}`", topic=topic)

            async with asyncio.TaskGroup() as tasks:
                async for message in client.messages:
                    await consume_message(
                        callback=callback,
                        message=message,
                        db=db,
                        tasks=tasks,
                    )
    except aiomqtt.MqttError as error:
        logfire.exception("Lost connection to the broker. Please restart the consumer")
        raise asyncio.CancelledError from error


async def loop_consume_messages(
    *,
    callback: Callback,
    settings: Settings,
    topics: list[str],
) -> None:
    async with get_db(settings.db_path) as db:
        try:
            while True:
                await consume_messages(
                    callback=callback,
                    db=db,
                    settings=settings,
                    topics=topics,
                )
        except asyncio.CancelledError:
            return
