"""tipos servicio valores

Revision ID: 202606150001
Revises: 202605290004
Create Date: 2026-06-15 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606150001"
down_revision: str | None = "202605290004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tipos_servicio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("esta_activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.bulk_insert(
        sa.table(
            "tipos_servicio",
            sa.column("id", sa.Integer),
            sa.column("nombre", sa.String),
            sa.column("valor", sa.Numeric),
            sa.column("esta_activo", sa.Boolean),
        ),
        [
            {"id": 1, "nombre": "Mantenimiento", "valor": 0, "esta_activo": True},
            {"id": 2, "nombre": "Diagnostico", "valor": 0, "esta_activo": True},
            {"id": 3, "nombre": "Soporte vial", "valor": 0, "esta_activo": True},
        ],
    )
    op.execute(
        "SELECT setval(pg_get_serial_sequence('tipos_servicio', 'id'), "
        "(SELECT max(id) FROM tipos_servicio))"
    )

    op.add_column(
        "servicios", sa.Column("tipo_servicio_nombre", sa.String(length=120), nullable=True)
    )
    op.add_column("servicios", sa.Column("valor_servicio", sa.Numeric(12, 2), nullable=True))
    op.alter_column("servicios", "tipo_servicio", type_=sa.Integer())
    op.execute(
        """
        UPDATE servicios
        SET tipo_servicio_nombre = tipos_servicio.nombre,
            valor_servicio = tipos_servicio.valor
        FROM tipos_servicio
        WHERE servicios.tipo_servicio = tipos_servicio.id
        """
    )
    op.execute(
        """
        UPDATE servicios
        SET tipo_servicio_nombre = COALESCE(tipo_servicio_nombre, 'Tipo ' || tipo_servicio),
            valor_servicio = COALESCE(valor_servicio, 0)
        """
    )
    op.alter_column("servicios", "tipo_servicio_nombre", nullable=False)
    op.alter_column("servicios", "valor_servicio", nullable=False)

    op.drop_constraint("ck_servicios_tipo_servicio", "servicios", type_="check")
    op.create_foreign_key(
        "fk_servicios_tipo_servicio",
        "servicios",
        "tipos_servicio",
        ["tipo_servicio"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_servicios_tipo_servicio", "servicios", type_="foreignkey")
    op.create_check_constraint(
        "ck_servicios_tipo_servicio",
        "servicios",
        "tipo_servicio IN (1, 2, 3)",
    )
    op.drop_column("servicios", "valor_servicio")
    op.drop_column("servicios", "tipo_servicio_nombre")
    op.alter_column("servicios", "tipo_servicio", type_=sa.SmallInteger())
    op.drop_table("tipos_servicio")
