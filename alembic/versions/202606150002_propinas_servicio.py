"""propinas servicio

Revision ID: 202606150002
Revises: 202606150001
Create Date: 2026-06-15 00:02:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202606150002"
down_revision: str | None = "202606150001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "propinas_servicio",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tecnico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["empresa_cliente_id"], ["empresas_cliente.id"]),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"]),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnicos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("servicio_id", name="uq_propinas_servicio_id"),
    )

    op.add_column("reportes_pago", sa.Column("valor_base", sa.Numeric(12, 2), nullable=True))
    op.add_column("reportes_pago", sa.Column("valor_propina", sa.Numeric(12, 2), nullable=True))
    op.execute(
        """
        UPDATE reportes_pago
        SET valor_base = COALESCE(valor, 0),
            valor_propina = 0
        """
    )
    op.alter_column("reportes_pago", "valor_base", nullable=False)
    op.alter_column("reportes_pago", "valor_propina", nullable=False)


def downgrade() -> None:
    op.drop_column("reportes_pago", "valor_propina")
    op.drop_column("reportes_pago", "valor_base")
    op.drop_table("propinas_servicio")
