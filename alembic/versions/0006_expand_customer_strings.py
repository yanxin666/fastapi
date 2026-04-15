"""Expand customers string columns

Revision ID: 0006_expand_customer_strings
Revises: 0005_add_followup_at
Create Date: 2026-04-15 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_expand_customer_strings"
down_revision = "0005_add_followup_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # String(20) → String(64)
    op.alter_column("customers", "phone", type_=sa.String(64))
    op.alter_column("customers", "wechat_status", type_=sa.String(64))
    op.alter_column("customers", "qq", type_=sa.String(64))
    op.alter_column("customers", "intention", type_=sa.String(64))
    op.alter_column("customers", "feedback_status", type_=sa.String(64))
    op.alter_column("customers", "customer_stage", type_=sa.String(64))
    op.alter_column("customers", "assign_method", type_=sa.String(64))

    # String(32) → String(128)
    op.alter_column("customers", "province", type_=sa.String(128))
    op.alter_column("customers", "region", type_=sa.String(128))
    op.alter_column("customers", "grade", type_=sa.String(128))
    op.alter_column("customers", "assign_type", type_=sa.String(128))
    op.alter_column("customers", "ip_province", type_=sa.String(128))
    op.alter_column("customers", "ip_city", type_=sa.String(128))

    # String(64) → String(256)
    op.alter_column("customers", "name", type_=sa.String(256))
    op.alter_column("customers", "wechat", type_=sa.String(256))
    op.alter_column("customers", "source_name", type_=sa.String(256))
    op.alter_column("customers", "owner", type_=sa.String(256))
    op.alter_column("customers", "primary_project", type_=sa.String(256))
    op.alter_column("customers", "project", type_=sa.String(256))
    op.alter_column("customers", "business_dept", type_=sa.String(256))
    op.alter_column("customers", "call_dept", type_=sa.String(256))
    op.alter_column("customers", "call_group", type_=sa.String(256))
    op.alter_column("customers", "advertiser", type_=sa.String(256))
    op.alter_column("customers", "creator", type_=sa.String(256))
    op.alter_column("customers", "creator_org", type_=sa.String(256))
    op.alter_column("customers", "first_consultant", type_=sa.String(256))
    op.alter_column("customers", "last_consultant", type_=sa.String(256))
    op.alter_column("customers", "first_assign_org", type_=sa.String(256))
    op.alter_column("customers", "first_assign_person", type_=sa.String(256))
    op.alter_column("customers", "last_first_consult_person", type_=sa.String(256))
    op.alter_column("customers", "ip", type_=sa.String(256))
    op.alter_column("customers", "original_id", type_=sa.String(256))

    # String(128) → String(512)
    op.alter_column("customers", "tag", type_=sa.String(512))

    # String(256) → Text（URL 长度不可预期）
    op.alter_column("customers", "landing_page", type_=sa.Text)


def downgrade() -> None:
    # 恢复原始大小（仅结构回退，不截断已有数据）
    op.alter_column("customers", "landing_page", type_=sa.String(256))
    op.alter_column("customers", "tag", type_=sa.String(128))
    op.alter_column("customers", "name", type_=sa.String(64))
    op.alter_column("customers", "phone", type_=sa.String(20))
    op.alter_column("customers", "wechat", type_=sa.String(64))
    op.alter_column("customers", "wechat_status", type_=sa.String(20))
    op.alter_column("customers", "qq", type_=sa.String(20))
    op.alter_column("customers", "province", type_=sa.String(32))
    op.alter_column("customers", "region", type_=sa.String(32))
    op.alter_column("customers", "grade", type_=sa.String(32))
    op.alter_column("customers", "intention", type_=sa.String(20))
    op.alter_column("customers", "feedback_status", type_=sa.String(20))
    op.alter_column("customers", "customer_stage", type_=sa.String(20))
    op.alter_column("customers", "source_name", type_=sa.String(64))
    op.alter_column("customers", "owner", type_=sa.String(64))
    op.alter_column("customers", "primary_project", type_=sa.String(64))
    op.alter_column("customers", "project", type_=sa.String(64))
    op.alter_column("customers", "business_dept", type_=sa.String(64))
    op.alter_column("customers", "call_dept", type_=sa.String(64))
    op.alter_column("customers", "call_group", type_=sa.String(64))
    op.alter_column("customers", "advertiser", type_=sa.String(64))
    op.alter_column("customers", "assign_method", type_=sa.String(20))
    op.alter_column("customers", "assign_type", type_=sa.String(32))
    op.alter_column("customers", "creator", type_=sa.String(64))
    op.alter_column("customers", "creator_org", type_=sa.String(64))
    op.alter_column("customers", "first_consultant", type_=sa.String(64))
    op.alter_column("customers", "last_consultant", type_=sa.String(64))
    op.alter_column("customers", "first_assign_org", type_=sa.String(64))
    op.alter_column("customers", "first_assign_person", type_=sa.String(64))
    op.alter_column("customers", "last_first_consult_person", type_=sa.String(64))
    op.alter_column("customers", "ip", type_=sa.String(64))
    op.alter_column("customers", "ip_province", type_=sa.String(32))
    op.alter_column("customers", "ip_city", type_=sa.String(32))
    op.alter_column("customers", "original_id", type_=sa.String(64))
