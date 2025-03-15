import asyncio
from datetime import datetime
from typing import Annotated, Literal, NewType, Self

import logfire
import typer
from pydantic import AfterValidator, BeforeValidator, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import TIMESTAMP, Column, Field, SQLModel, delete, text
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.main import SQLModelConfig  # type: ignore[attr-defined]

from consumer.settings import Settings, get_db

cli = typer.Typer()

type Choices = Literal[0, 1, 2, 3]
type DeviceID = str
DeletedTotal = NewType("DeletedTotal", int)


class Answer(SQLModel, table=True):
    __tablename__ = "answers"

    model_config = SQLModelConfig(validate_assignment=True)

    received_at: Annotated[
        datetime | None,
        Field(
            default=None,
            repr=False,
            exclude=True,
            sa_column=Column(
                TIMESTAMP(timezone=True),
                nullable=False,
                server_default=text("CURRENT_TIMESTAMP"),
            ),
        ),
    ]
    device_id: Annotated[str, Field(primary_key=True)]  # can't use DeviceID directly
    question_id: Annotated[str, BeforeValidator(str.strip), Field(primary_key=True)]
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


async def save_answer(answer: Answer, db: AsyncEngine) -> bool:
    # Committing the answer cleans the model, so save its representation for later
    async with AsyncSession(db, expire_on_commit=False) as session:
        session.add(answer)
        try:
            await session.commit()
        except IntegrityError:
            # Assumption: integrity check can only fail for duplicate PKs
            logfire.error("Skipped {answer} (already answered)", answer=answer)
            await session.rollback()
        except SQLAlchemyError:
            logfire.exception(
                "Ignoring exception during persisting {answer}",
                answer=answer,
            )
        else:
            logfire.info("Saved {answer}", answer=answer)
            return True
    return False


async def prune_all_answers(*, settings: Settings) -> DeletedTotal:
    async with get_db(settings.db_path) as db, AsyncSession(db) as session:
        result = await session.exec(delete(Answer).returning(Answer))  # type: ignore[call-overload]
        total = len(result.fetchall())
        await session.commit()
    return DeletedTotal(total)


@cli.command("prune")
def command_prune() -> None:
    total = asyncio.run(prune_all_answers(settings=Settings()))
    logfire.info("Pruned {total} answer(s)", total=total)
