import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from consumer.answers import Answer


@pytest.mark.asyncio
async def test_many_answers_to_same_question_disallowed(
    test_db: AsyncSession,
    sample_answers: list[Answer],
) -> None:
    with pytest.raises(IntegrityError):  # noqa: PT012
        test_db.add_all(sample_answers)
        test_db.add_all(sample_answers)
        await test_db.commit()
