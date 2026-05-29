"""crear tablas iniciales

Revision ID: 202605270001
Revises:
Create Date: 2026-05-27 00:01:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605270001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def columna_uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "usuarios",
        columna_uuid_pk(),
        sa.Column("nombre_completo", sa.String(length=150), nullable=False),
        sa.Column("correo", sa.String(length=150), nullable=False),
        sa.Column("hash_contrasena", sa.Text(), nullable=False),
        sa.Column("telefono", sa.String(length=50), nullable=True),
        sa.Column("numero_documento", sa.String(length=50), nullable=True),
        sa.Column("ciudad", sa.String(length=100), nullable=True),
        sa.Column("municipio", sa.String(length=100), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("eps", sa.String(length=100), nullable=True),
        sa.Column("arl", sa.String(length=100), nullable=True),
        sa.Column("tiene_vehiculo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("placa_vehiculo", sa.String(length=30), nullable=True),
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
    op.create_index("ix_usuarios_correo", "usuarios", ["correo"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre", name="uq_roles_nombre"),
    )

    op.create_table(
        "empresas_cliente",
        columna_uuid_pk(),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("identificacion_tributaria", sa.String(length=80), nullable=True),
        sa.Column("correo_contacto", sa.String(length=150), nullable=True),
        sa.Column("telefono_contacto", sa.String(length=50), nullable=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hash_api_key", sa.Text(), nullable=True),
        sa.Column("esta_activa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", name="uq_empresas_cliente_usuario_id"),
    )

    op.create_table(
        "configuracion_app",
        sa.Column("clave", sa.String(length=100), nullable=False),
        sa.Column("valor", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("clave"),
    )

    op.create_table(
        "usuario_roles",
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("usuario_id", "rol_id"),
    )

    op.create_table(
        "tecnicos",
        columna_uuid_pk(),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "ubicacion_actual",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
        sa.Column("esta_disponible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fecha_ultima_ubicacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", name="uq_tecnicos_usuario_id"),
    )
    op.create_index(
        "idx_tecnicos_ubicacion_actual",
        "tecnicos",
        ["ubicacion_actual"],
        postgresql_using="gist",
    )

    op.create_table(
        "servicios",
        columna_uuid_pk(),
        sa.Column("empresa_cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_servicio", sa.SmallInteger(), nullable=False),
        sa.Column("placa_vehiculo", sa.String(length=30), nullable=True),
        sa.Column(
            "ubicacion",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=False,
        ),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("fecha_programada", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "estado", sa.String(length=50), nullable=False, server_default=sa.text("'CREADO'")
        ),
        sa.Column("tecnico_aceptado_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fecha_aceptacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_finalizacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_validacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_pago_generado", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clave_idempotencia", sa.String(length=150), nullable=False),
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
        sa.CheckConstraint("tipo_servicio IN (1, 2, 3)", name="ck_servicios_tipo_servicio"),
        sa.CheckConstraint(
            "estado IN ('CREADO', 'DISPONIBLE', 'ACEPTADO', 'EN_PROCESO', 'FINALIZADO', "
            "'VALIDADO', 'PAGO_GENERADO', 'RECHAZADO', 'REPROGRAMACION_SOLICITADA', "
            "'CANCELADO')",
            name="ck_servicios_estado",
        ),
        sa.ForeignKeyConstraint(["empresa_cliente_id"], ["empresas_cliente.id"]),
        sa.ForeignKeyConstraint(["tecnico_aceptado_id"], ["tecnicos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "empresa_cliente_id",
            "clave_idempotencia",
            name="uq_servicios_empresa_cliente_id_clave_idempotencia",
        ),
    )
    op.create_index("ix_servicios_estado", "servicios", ["estado"], unique=False)
    op.create_index("idx_servicios_ubicacion", "servicios", ["ubicacion"], postgresql_using="gist")

    op.create_table(
        "notificaciones_servicio",
        columna_uuid_pk(),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tecnico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "estado", sa.String(length=30), nullable=False, server_default=sa.text("'ENVIADA'")
        ),
        sa.Column(
            "fecha_envio",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("fecha_lectura", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado IN ('ENVIADA', 'LEIDA', 'ACEPTADA', 'RECHAZADA')",
            name="ck_notificaciones_servicio_estado",
        ),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"]),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnicos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "servicio_id", "tecnico_id", name="uq_notificaciones_servicio_servicio_id_tecnico_id"
        ),
    )

    op.create_table(
        "rechazos_servicio",
        columna_uuid_pk(),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tecnico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"]),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnicos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "servicio_id", "tecnico_id", name="uq_rechazos_servicio_servicio_id_tecnico_id"
        ),
    )

    op.create_table(
        "reprogramaciones_servicio",
        columna_uuid_pk(),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tecnico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_propuesta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "estado", sa.String(length=30), nullable=False, server_default=sa.text("'PENDIENTE'")
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE', 'APROBADA', 'RECHAZADA')",
            name="ck_reprogramaciones_servicio_estado",
        ),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"]),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnicos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "evidencias_servicio",
        columna_uuid_pk(),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subido_por_usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url_archivo", sa.Text(), nullable=False),
        sa.Column("tipo_archivo", sa.String(length=50), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "estado_aprobacion",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'PENDIENTE'"),
        ),
        sa.Column("aprobado_por_usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fecha_aprobacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "estado_aprobacion IN ('PENDIENTE', 'APROBADA', 'RECHAZADA')",
            name="ck_evidencias_servicio_estado_aprobacion",
        ),
        sa.ForeignKeyConstraint(["aprobado_por_usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"]),
        sa.ForeignKeyConstraint(["subido_por_usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reportes_pago",
        columna_uuid_pk(),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tecnico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "estado", sa.String(length=30), nullable=False, server_default=sa.text("'PENDIENTE'")
        ),
        sa.Column(
            "fecha_generacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE', 'GENERADO', 'PAGADO', 'ANULADO')",
            name="ck_reportes_pago_estado",
        ),
        sa.ForeignKeyConstraint(["empresa_cliente_id"], ["empresas_cliente.id"]),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"]),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnicos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("servicio_id", name="uq_reportes_pago_servicio_id"),
    )

    op.create_table(
        "sedes",
        columna_uuid_pk(),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column(
            "ubicacion",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sedes_nombre", "sedes", ["nombre"], unique=True)
    op.create_index("idx_sedes_ubicacion", "sedes", ["ubicacion"], postgresql_using="gist")

    op.create_table(
        "calificaciones_servicio",
        columna_uuid_pk(),
        sa.Column("servicio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("empresa_cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tecnico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("puntuacion", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column(
            "fecha_calificacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("puntuacion BETWEEN 1 AND 5", name="ck_calificaciones_puntuacion"),
        sa.ForeignKeyConstraint(["empresa_cliente_id"], ["empresas_cliente.id"]),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"]),
        sa.ForeignKeyConstraint(["tecnico_id"], ["tecnicos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("servicio_id", name="uq_calificaciones_servicio_id"),
    )

    op.bulk_insert(
        sa.table("roles", sa.column("id", sa.Integer), sa.column("nombre", sa.String)),
        [
            {"id": 1, "nombre": "TECNICO"},
            {"id": 2, "nombre": "EMPRESA_CLIENTE"},
            {"id": 3, "nombre": "ADMIN"},
        ],
    )
    op.execute("SELECT setval(pg_get_serial_sequence('roles', 'id'), 3, true)")
    op.execute(
        """
        INSERT INTO configuracion_app (clave, valor)
        VALUES (
            'aprobacion_evidencias',
            '{"modo": "MANUAL", "roles_permitidos": ["ADMIN"]}'::jsonb
        )
        """
    )


def downgrade() -> None:
    op.drop_index("idx_sedes_ubicacion", table_name="sedes", postgresql_using="gist")
    op.drop_index("ix_sedes_nombre", table_name="sedes")
    op.drop_table("sedes")
    op.drop_table("calificaciones_servicio")
    op.drop_table("reportes_pago")
    op.drop_table("evidencias_servicio")
    op.drop_table("reprogramaciones_servicio")
    op.drop_table("rechazos_servicio")
    op.drop_table("notificaciones_servicio")
    op.drop_index("idx_servicios_ubicacion", table_name="servicios", postgresql_using="gist")
    op.drop_index("ix_servicios_estado", table_name="servicios")
    op.drop_table("servicios")
    op.drop_index("idx_tecnicos_ubicacion_actual", table_name="tecnicos", postgresql_using="gist")
    op.drop_table("tecnicos")
    op.drop_table("usuario_roles")
    op.drop_table("configuracion_app")
    op.drop_table("empresas_cliente")
    op.drop_table("roles")
    op.drop_index("ix_usuarios_correo", table_name="usuarios")
    op.drop_table("usuarios")
