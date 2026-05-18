"""Add claim_status column to customers

Revision ID: 0007_add_customer_claim_status
Revises: 0006_expand_customer_strings
Create Date: 2026-05-19 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_add_customer_claim_status"
down_revision = "0006_expand_customer_strings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 新增 claim_status 冗余列，与 user_id 模式一致，加速按认领状态筛选
    op.add_column(
        "customers",
        sa.Column("claim_status", sa.String(20), nullable=True),
    )

    # 回填：已有 user_id 的客户标记为 claimed，其余保持 NULL（公海）
    op.execute(
        "UPDATE customers SET claim_status = 'claimed' "
        "WHERE user_id IS NOT NULL AND is_deleted = false"
    )

    # 创建索引，加速按认领状态筛选
    op.create_index("ix_customers_claim_status", "customers", ["claim_status"])


def downgrade() -> None:
    op.drop_index("ix_customers_claim_status", table_name="customers")
    op.drop_column("customers", "claim_status")
