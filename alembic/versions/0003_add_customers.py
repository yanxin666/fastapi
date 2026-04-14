"""Add customers table

Revision ID: 0003_add_customers
Revises: 0002_auth_core
Create Date: 2026-04-14 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

CUSTOMER_UPDATED_AT_TRIGGER_PG = """
CREATE OR REPLACE FUNCTION update_customers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_customers_updated_at();
"""

CUSTOMER_UPDATED_AT_TRIGGER_SQLITE = """
CREATE TRIGGER update_customers_updated_at
AFTER UPDATE ON customers
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE customers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""

revision = "0003_add_customers"
down_revision = "0002_auth_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # 基本信息
        sa.Column("name", sa.String(64), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("wechat", sa.String(64), nullable=True),
        sa.Column("wechat_status", sa.String(20), nullable=True),
        sa.Column("qq", sa.String(20), nullable=True),
        sa.Column("province", sa.String(32), nullable=True),
        sa.Column("region", sa.String(32), nullable=True),
        sa.Column("grade", sa.String(32), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("tag", sa.String(128), nullable=True),
        # 意向与状态
        sa.Column("intention", sa.String(20), nullable=True),
        sa.Column("feedback_status", sa.String(20), nullable=True),
        sa.Column("customer_stage", sa.String(20), nullable=True),
        # 来源与归属
        sa.Column("source_name", sa.String(64), nullable=True),
        sa.Column("owner", sa.String(64), nullable=True),
        sa.Column("primary_project", sa.String(64), nullable=True),
        sa.Column("project", sa.String(64), nullable=True),
        sa.Column("business_dept", sa.String(64), nullable=True),
        sa.Column("call_dept", sa.String(64), nullable=True),
        sa.Column("call_group", sa.String(64), nullable=True),
        sa.Column("advertiser", sa.String(64), nullable=True),
        sa.Column("landing_page", sa.String(256), nullable=True),
        # 分配信息
        sa.Column("assign_method", sa.String(20), nullable=True),
        sa.Column("assign_type", sa.String(32), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creator", sa.String(64), nullable=True),
        sa.Column("creator_org", sa.String(64), nullable=True),
        # 咨询信息
        sa.Column("first_consultant", sa.String(64), nullable=True),
        sa.Column("last_consultant", sa.String(64), nullable=True),
        sa.Column("first_assign_org", sa.String(64), nullable=True),
        sa.Column("first_assign_person", sa.String(64), nullable=True),
        sa.Column("first_assign_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_first_consult_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_first_consult_person", sa.String(64), nullable=True),
        # 统计追踪
        sa.Column(
            "registration_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "daily_outbound_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "daily_connected_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "daily_connected_duration",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("ip_province", sa.String(32), nullable=True),
        sa.Column("ip_city", sa.String(32), nullable=True),
        # 聊天记录
        sa.Column("raw_chat_records", sa.Text(), nullable=True),
        sa.Column("chat_records", sa.Text(), nullable=True),
        # 系统字段
        sa.Column("original_id", sa.String(64), nullable=True),
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
    )

    # 创建索引
    op.create_index(op.f("ix_customers_phone"), "customers", ["phone"])
    op.create_index(op.f("ix_customers_name"), "customers", ["name"])
    op.create_index(
        op.f("ix_customers_feedback_status"), "customers", ["feedback_status"]
    )
    op.create_index(
        op.f("ix_customers_customer_stage"), "customers", ["customer_stage"]
    )
    op.create_index(op.f("ix_customers_owner"), "customers", ["owner"])
    op.create_index(op.f("ix_customers_is_deleted"), "customers", ["is_deleted"])
    op.create_index(op.f("ix_customers_created_at"), "customers", ["created_at"])

    # 创建 updated_at 触发器（PostgreSQL）
    op.execute(CUSTOMER_UPDATED_AT_TRIGGER_PG)


def downgrade() -> None:
    # 删除触发器和函数（PostgreSQL）
    op.execute("DROP TRIGGER IF EXISTS update_customers_updated_at ON customers")
    op.execute("DROP FUNCTION IF EXISTS update_customers_updated_at() CASCADE")

    op.drop_index(op.f("ix_customers_created_at"), table_name="customers")
    op.drop_index(op.f("ix_customers_is_deleted"), table_name="customers")
    op.drop_index(op.f("ix_customers_owner"), table_name="customers")
    op.drop_index(op.f("ix_customers_customer_stage"), table_name="customers")
    op.drop_index(op.f("ix_customers_feedback_status"), table_name="customers")
    op.drop_index(op.f("ix_customers_name"), table_name="customers")
    op.drop_index(op.f("ix_customers_phone"), table_name="customers")
    op.drop_table("customers")
