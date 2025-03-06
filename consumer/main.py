import argparse
import asyncio
from datetime import datetime
from typing import Annotated, Literal, Self, assert_never

import aiomqtt
import logfire
from pydantic import AfterValidator, TypeAdapter, ValidationError
from pydantic_extra_types.mac_address import MacAddress
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import TIMESTAMP, Column, Field, SQLModel, delete, text
from sqlmodel.ext.asyncio.session import AsyncSession

from consumer.settings import Settings, create_db, get_mqtt_client

type Choices = Literal[0, 1, 2, 3]

ANSWER_TOPIC = "answer"


class Answer(SQLModel, table=True):
    __tablename__ = "answers"

    received_at: Annotated[
        datetime | None,
        Field(
            default=None,
            repr=False,
            sa_column=Column(
                TIMESTAMP(timezone=True),
                nullable=False,
                server_default=text("CURRENT_TIMESTAMP"),
            ),
        ),
    ]
    device_id: Annotated[MacAddress, Field(primary_key=True)]
    question_id: Annotated[str, Field(primary_key=True)]
    choice: Annotated[int, AfterValidator(TypeAdapter(Choices).validate_python)]

    @classmethod
    def from_message(cls, message: str, *, sep: str = "|") -> Self:
        """
        Load the answer from message string.

        >>> Answer.from_message("00-B0-D0-63-C2-26|spam|2")
        Answer(device_id='00:b0:d0:63:c2:26', question_id='spam', choice=2)

        >>> Answer.from_message("FF-DE-AD-BE-EF-FF|who|expected|that|1")
        Answer(device_id='ff:de:ad:be:ef:ff', question_id='who|expected|that', choice=1)

        >>> Answer.from_message("C0-FF-EE-F0-40-23;foo;bar;3", sep=";")
        Answer(device_id='c0:ff:ee:f0:40:23', question_id='foo;bar', choice=3)

        >>> Answer.from_message(  # doctest: +IGNORE_EXCEPTION_DETAIL
        ...     "C0-FF-ZZ-F0-40-23;foobar;3",
        ...     sep=";"
        ... )
        Traceback (most recent call last):
        ...
        ValidationError: device_id
        """
        try:
            device_id, details = message.split(sep, 1)
            question_id, choice = details.rsplit(sep, 1)
        except ValueError as error:
            msg = "expected message in format <MAC-address>|<question ID>|<choice>"
            raise ValidationError(msg) from error
        return cls.model_validate(
            {"device_id": device_id, "question_id": question_id, "choice": choice}
        )


async def handle_answer(answer: Answer, db: AsyncEngine) -> None:
    # Committing the answer cleans the model, so save its representation for later
    answer_handled = str(answer)
    async with AsyncSession(db) as session:
        session.add(answer)
        try:
            await session.commit()
        except IntegrityError:
            # Assumption: integrity check can only fail for duplicate PKs
            logfire.error("Skipped {answer} (already answered)", answer=answer_handled)
            await session.rollback()
        except SQLAlchemyError:
            logfire.exception(
                "Ignoring exception during persisting {answer}",
                answer=answer_handled,
            )
        else:
            logfire.debug("Saved {answer}", answer=answer_handled)


async def consume_answer(
    message: aiomqtt.Message,
    db: AsyncEngine,
    tasks: asyncio.TaskGroup,
) -> None:
    assert message.topic.matches(ANSWER_TOPIC)
    # `.payload` attribute values in the received messages are always `bytes`
    # TODO(#1): Report `aiomqtt.types.PayloadType` is incorrectly used upstream
    assert isinstance(message.payload, bytes)

    try:
        answer = Answer.from_message(message.payload.decode())
    except ValueError:
        logfire.exception("Ignoring incorrect payload")
        return

    tasks.create_task(handle_answer(answer, db))
    logfire.debug("Dispatched {answer}", answer=answer)

    await asyncio.sleep(0)


async def loop_consume_once(db: AsyncEngine, settings: Settings) -> None:
    try:
        async with get_mqtt_client(settings.mqtt) as client:
            await client.subscribe(ANSWER_TOPIC)
            logfire.info("Subscribed to `{topic}`", topic=ANSWER_TOPIC)

            async with asyncio.TaskGroup() as tasks:
                async for message in client.messages:
                    await consume_answer(message, db, tasks)
    except aiomqtt.MqttError as error:
        logfire.error("Lost connection to the broker. Please restart the consumer")
        raise asyncio.CancelledError from error


async def loop_consume(settings: Settings) -> None:
    db = create_db(settings.db_path)

    try:
        while True:
            await loop_consume_once(db, settings)
    except asyncio.CancelledError:
        return
    finally:
        await db.dispose()


async def prune_all_answers(settings: Settings) -> None:
    db = create_db(settings.db_path)

    try:
        async with AsyncSession(db) as session:
            await session.exec(delete(Answer))  # type: ignore[call-overload]
            await session.commit()
    finally:
        await db.dispose()

    logfire.info("Pruned all answers")


def main() -> None:
    settings = Settings()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        default="consume",
        choices=["consume", "prune"],
        nargs="?",
    )
    args = parser.parse_args()

    match args.command:
        case "consume":
            task = loop_consume(settings)
        case "prune":
            task = prune_all_answers(settings)
        case _:
            assert_never(args.command)

    logfire.configure(inspect_arguments=False)
    asyncio.run(task)


if __name__ == "__main__":
    main()
