"""Trazabilidad de notificaciones FCM."""

from alembic import op
import sqlalchemy as sa

revision = "202607010001"
down_revision = "202606150002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tecnicos", sa.Column("fcm_token", sa.Text(), nullable=True))
    op.add_column("tecnicos", sa.Column("fecha_fcm_token", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "notificaciones_servicio",
        sa.Column("estado_entrega", sa.String(length=30), nullable=False, server_default="PENDIENTE"),
    )
    op.add_column("notificaciones_servicio", sa.Column("fcm_message_id", sa.Text(), nullable=True))
    op.add_column("notificaciones_servicio", sa.Column("error_entrega", sa.Text(), nullable=True))
    op.add_column("notificaciones_servicio", sa.Column("fecha_entrega_proveedor", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notificaciones_servicio", sa.Column("fecha_recibida_app", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for columna in ["fecha_recibida_app", "fecha_entrega_proveedor", "error_entrega", "fcm_message_id", "estado_entrega"]:
        op.drop_column("notificaciones_servicio", columna)
    op.drop_column("tecnicos", "fecha_fcm_token")
    op.drop_column("tecnicos", "fcm_token")
