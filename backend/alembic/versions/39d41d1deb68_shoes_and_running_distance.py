"""shoes and running distance

Revision ID: 39d41d1deb68
Revises: fcaf889cd709
Create Date: 2026-08-25 15:45:41.506454

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "39d41d1deb68"
down_revision: str | None = "fcaf889cd709"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shoes_user_id"), "shoes", ["user_id"], unique=False)

    # batch mode: SQLite no soporta ALTER para añadir una FK constraint directamente,
    # necesita recrear la tabla (transparente en Postgres, que sí soporta el ALTER simple).
    with op.batch_alter_table("workout_sessions") as batch_op:
        batch_op.add_column(sa.Column("running_distance_km", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("shoe_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_workout_sessions_shoe_id_shoes",
            "shoes",
            ["shoe_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("workout_sessions") as batch_op:
        batch_op.drop_constraint("fk_workout_sessions_shoe_id_shoes", type_="foreignkey")
        batch_op.drop_column("shoe_id")
        batch_op.drop_column("running_distance_km")
    op.drop_index(op.f("ix_shoes_user_id"), table_name="shoes")
    op.drop_table("shoes")
