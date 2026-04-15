"""Add followup_at to customers

Revision ID: 0005_add_followup_at
Revises: 0004_add_claim_followup
Create Date: 2026-04-15 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_add_followup_at"
down_revision = "0004_add_claim_followup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("followup_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customers", "followup_at")
