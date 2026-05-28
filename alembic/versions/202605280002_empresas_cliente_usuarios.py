"""vincular empresas cliente con usuarios

Revision ID: 202605280002
Revises: 202605270001
Create Date: 2026-05-28 00:02:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605280002"
down_revision: str | None = "202605270001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "empresas_cliente",
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_empresas_cliente_usuario_id_usuarios",
        "empresas_cliente",
        "usuarios",
        ["usuario_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_empresas_cliente_usuario_id",
        "empresas_cliente",
        ["usuario_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_empresas_cliente_usuario_id", "empresas_cliente", type_="unique")
    op.drop_constraint(
        "fk_empresas_cliente_usuario_id_usuarios", "empresas_cliente", type_="foreignkey"
    )
    op.drop_column("empresas_cliente", "usuario_id")
