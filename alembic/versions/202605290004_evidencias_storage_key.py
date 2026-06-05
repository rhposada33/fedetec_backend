"""agregar storage key a evidencias

Revision ID: 202605290004
Revises: 202605290003
Create Date: 2026-05-29 00:04:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202605290004"
down_revision: str | None = "202605290003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columnas = {columna["name"] for columna in inspector.get_columns("evidencias_servicio")}

    if "storage_key" in columnas:
        return

    op.add_column("evidencias_servicio", sa.Column("storage_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("evidencias_servicio", "storage_key")
