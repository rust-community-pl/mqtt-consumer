# ruff: noqa: E501,W291
"""
${message[0:1].upper() + message[1:].removesuffix(".") + "."}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Created: ${create_date}
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
${imports if imports else ""}
revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}