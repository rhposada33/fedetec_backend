"""crear calificaciones servicio

Revision ID: 202605290003
Revises: 202605280002
Create Date: 2026-05-29 00:03:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605290003"
down_revision: str | None = "202605280002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "calificaciones_servicio" in inspector.get_table_names():
        return

    op.create_table(
        "calificaciones_servicio",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tecnico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("puntuacion", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column(
            "fecha_calificacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("puntuacion BETWEEN 1 AND 5", name="ck_calificaciones_puntuacion"),
        sa.ForeignKeyConstraint(["empresa_cliente_id"], ["empresas_cliente.id"]),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"]),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnicos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("servicio_id", name="uq_calificaciones_servicio_id"),
    )


def downgrade() -> None:
    op.drop_table("calificaciones_servicio")
