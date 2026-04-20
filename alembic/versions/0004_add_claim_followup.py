"""Add claim and followup tables

Revision ID: 0004_add_claim_followup
Revises: 0003_add_customers
Create Date: 2026-04-14 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_add_claim_followup"
down_revision = "0003_add_customers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. customers 表新增 user_id 列（认领用户 FK）
    op.add_column(
        "customers",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_customers_user_id", "customers", "users", ["user_id"], ["id"]
    )
    op.create_index(op.f("ix_customers_user_id"), "customers", ["user_id"])

    # 2. 认领策略表
    op.create_table(
        "claim_strategies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "max_claim_count",
            sa.Integer(),
            nullable=False,
            server_default="50",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_claim_strategies_user_id"),
        "claim_strategies",
        ["user_id"],
        unique=True,
    )

    # 3. 认领记录表
    op.create_table(
        "claim_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("claim_status", sa.String(20), nullable=False),
        sa.Column("claim_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        op.f("ix_claim_records_customer_id"), "claim_records", ["customer_id"]
    )
    op.create_index(
        "ix_claim_records_user_status",
        "claim_records",
        ["user_id", "claim_status"],
    )
    op.create_index(
        "ix_claim_records_customer_status",
        "claim_records",
        ["customer_id", "claim_status"],
    )

    # 4. 跟进记录表
    op.create_table(
        "followup_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("contact_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("intention", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("next_followup_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        op.f("ix_followup_records_customer_id"), "followup_records", ["customer_id"]
    )
    op.create_index(
        "ix_followup_records_user_contact",
        "followup_records",
        ["user_id", "contact_time"],
    )
    op.create_index(
        op.f("ix_followup_records_next_followup"),
        "followup_records",
        ["next_followup_time"],
    )
    op.create_index(
        op.f("ix_followup_records_is_deleted"), "followup_records", ["is_deleted"]
    )


def downgrade() -> None:
    # 跟进记录表
    op.drop_index(op.f("ix_followup_records_is_deleted"), table_name="followup_records")
    op.drop_index(
        op.f("ix_followup_records_next_followup"), table_name="followup_records"
    )
    op.drop_index("ix_followup_records_user_contact", table_name="followup_records")
    op.drop_index(
        op.f("ix_followup_records_customer_id"), table_name="followup_records"
    )
    op.drop_table("followup_records")

    # 认领记录表
    op.drop_index("ix_claim_records_customer_status", table_name="claim_records")
    op.drop_index("ix_claim_records_user_status", table_name="claim_records")
    op.drop_index(op.f("ix_claim_records_customer_id"), table_name="claim_records")
    op.drop_table("claim_records")

    # 认领策略表
    op.drop_index(op.f("ix_claim_strategies_user_id"), table_name="claim_strategies")
    op.drop_table("claim_strategies")

    # customers 表移除 user_id 列
    op.drop_index(op.f("ix_customers_user_id"), table_name="customers")
    op.drop_constraint("fk_customers_user_id", "customers", type_="foreignkey")
    op.drop_column("customers", "user_id")
