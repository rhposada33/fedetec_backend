"""crear tablas iniciales

Revision ID: 202605270001
Revises:
Create Date: 2026-05-27 00:01:00.000000

"""
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa

from alembic import op

revision: str = "202605270001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("correo", sa.String(length=255), nullable=False),
        sa.Column("nombre_completo", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("es_activo", sa.Boolean(), nullable=False),
        sa.Column("es_superusuario", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuarios_correo"), "usuarios", ["correo"], unique=True)
    op.create_index(op.f("ix_usuarios_id"), "usuarios", ["id"], unique=False)

    op.create_table(
        "sedes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column(
            "ubicacion",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sedes_id"), "sedes", ["id"], unique=False)
    op.create_index(op.f("ix_sedes_nombre"), "sedes", ["nombre"], unique=True)
    op.create_index("idx_sedes_ubicacion", "sedes", ["ubicacion"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("idx_sedes_ubicacion", table_name="sedes", postgresql_using="gist")
    op.drop_index(op.f("ix_sedes_nombre"), table_name="sedes")
    op.drop_index(op.f("ix_sedes_id"), table_name="sedes")
    op.drop_table("sedes")
    op.drop_index(op.f("ix_usuarios_id"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_correo"), table_name="usuarios")
    op.drop_table("usuarios")

