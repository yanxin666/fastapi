"""
客户数据导入脚本

从 CSV 文件导入客户数据到数据库。
使用方式：将 doc/customer.xlsx 另存为 doc/customer.csv（UTF-8 编码），然后运行本脚本。

功能：
- 自动映射 CSV 列名到数据库字段名
- 处理日期格式转换
- 处理空值（空字符串转为 None）
- 批量插入到 customers 表
- 跳过表头行和字段说明行
- 支持断点续导（跳过已存在的 original_id 记录）

使用示例：
    # 从项目根目录执行
    .venv/Scripts/python.exe scripts/import_customers.py
    # 或通过 Makefile
    make import-customers
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

# 将项目根目录加入 sys.path，以便导入 app 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session_factory
from app.models.customer import Customer

# CSV 文件路径（默认从 doc/customer.csv 读取）
DEFAULT_CSV_PATH = PROJECT_ROOT / "doc" / "customer.csv"

# CSV 列名 → 数据库字段名的映射
# 用户需将 xlsx 另存为 csv，列名应与 xlsx 表头一致
COLUMN_MAPPING: dict[str, str] = {
    "姓名": "name",
    "联系电话": "phone",
    "微信": "wechat",
    "微信状态": "wechat_status",
    "QQ": "qq",
    "省份": "province",
    "地域": "region",
    "年级": "grade",
    "意向度": "intention",
    "反馈状态": "feedback_status",
    "客户阶段": "customer_stage",
    "来源名称": "source_name",
    "归属人": "owner",
    "一级项目": "primary_project",
    "项目": "project",
    "事业部": "business_dept",
    "呼叫部": "call_dept",
    "呼叫组": "call_group",
    "广告商": "advertiser",
    "着陆页": "landing_page",
    "分配方式": "assign_method",
    "分配类型": "assign_type",
    "分配时间": "assigned_at",
    "创建人": "creator",
    "创建人归属机构": "creator_org",
    "首次咨询师": "first_consultant",
    "最后咨询师": "last_consultant",
    "首次分配归属机构": "first_assign_org",
    "首次分配归属人": "first_assign_person",
    "首次分配时间": "first_assign_time",
    "最后一次首咨分配时间": "last_first_consult_time",
    "最后首咨分配归属人": "last_first_consult_person",
    "报名次数": "registration_count",
    "当日外呼次数": "daily_outbound_count",
    "当日呼通的次数": "daily_connected_count",
    "当日接通时长": "daily_connected_duration",
    "Ip": "ip",
    "Ip省份": "ip_province",
    "Ip城市": "ip_city",
    "备注": "remark",
    "标签": "tag",
    "无格式聊天记录": "raw_chat_records",
    "聊天记录": "chat_records",
    "客户ID": "original_id",
}

# 日期时间字段列表，需要做格式转换
DATETIME_FIELDS = {
    "assigned_at",
    "first_assign_time",
    "last_first_consult_time",
}

# 整数字段列表，需要做 int 转换
INTEGER_FIELDS = {
    "registration_count",
    "daily_outbound_count",
    "daily_connected_count",
    "daily_connected_duration",
}


def parse_datetime(value: str) -> datetime | None:
    """
    解析日期时间字符串

    支持常见格式：YYYY-MM-DD HH:MM:SS、YYYY/MM/DD HH:MM:SS、YYYY-MM-DD 等。
    解析失败返回 None。
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    # 常见的日期时间格式
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S.%f",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    print(f"  警告: 无法解析日期 '{value}'，跳过该字段")
    return None


def parse_int(value: str) -> int | None:
    """
    解析整数字符串

    空值或非数字返回 None。
    """
    if not value or not value.strip():
        return None

    try:
        return int(float(value.strip()))
    except (ValueError, TypeError):
        return None


def clean_value(field_name: str, raw_value: str) -> object:
    """
    清洗单个字段值

    - 空字符串 → None
    - 日期时间字段 → datetime 对象
    - 整数字段 → int
    - 其他字段 → 原始字符串
    """
    if not raw_value or not raw_value.strip():
        return None

    if field_name in DATETIME_FIELDS:
        return parse_datetime(raw_value)

    if field_name in INTEGER_FIELDS:
        return parse_int(raw_value)

    return raw_value.strip()


def row_to_customer_data(
    row: dict[str, str],
    header_map: dict[int, str],
) -> dict[str, object]:
    """
    将 CSV 行数据转换为 Customer 模型可接受的字段字典

    Args:
        row: CSV 行数据（列名→值的字典）
        header_map: CSV 列名→数据库字段名的映射

    Returns:
        字段名字典，可直接传给 Customer(**data)
    """
    data: dict[str, object] = {}

    for csv_col, db_field in header_map.items():
        raw_value = row.get(csv_col, "")
        value = clean_value(db_field, raw_value)
        if value is not None:
            data[db_field] = value

    return data


def import_customers(csv_path: Path | None = None) -> None:
    """
    执行客户数据导入

    Args:
        csv_path: CSV 文件路径，默认为 doc/customer.csv
    """
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH

    if not csv_path.exists():
        print(f"错误: CSV 文件不存在: {csv_path}")
        print("请将 doc/customer.xlsx 另存为 doc/customer.csv（UTF-8 编码）后再运行")
        sys.exit(1)

    SessionFactory = get_session_factory()
    db: Session = SessionFactory()

    try:
        # 读取已导入的 original_id 集合，用于跳过重复记录
        existing_ids = set(
            db.execute(
                select(Customer.original_id).where(Customer.original_id.isnot(None))
            )
            .scalars()
            .all()
        )

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            # 验证 CSV 列名是否在映射表中
            csv_headers = reader.fieldnames or []
            header_map: dict[str, str] = {}
            unknown_cols: list[str] = []

            for col in csv_headers:
                if col in COLUMN_MAPPING:
                    header_map[col] = COLUMN_MAPPING[col]
                elif col.strip():
                    # 忽略的列（如"表头"列）
                    unknown_cols.append(col)

            if unknown_cols:
                print(f"提示: 以下 CSV 列未映射，将被忽略: {unknown_cols}")

            imported_count = 0
            skipped_count = 0
            error_count = 0

            for row_num, row in enumerate(reader, start=2):
                # 跳过空行
                if not any(row.values()):
                    continue

                # 跳过字段说明行（包含换行符的枚举值行，Excel 最后一行常是这种行）
                if any("\n" in str(v) for v in row.values()):
                    continue

                data = row_to_customer_data(row, header_map)

                # 如果没有有效数据，跳过该行
                if not data:
                    continue

                # 通过 original_id 去重，跳过已导入的记录
                original_id = data.get("original_id")
                if original_id and original_id in existing_ids:
                    skipped_count += 1
                    continue

                try:
                    customer = Customer(**data)
                    db.add(customer)
                    imported_count += 1

                    # 每处理 100 条提交一次，减少内存占用
                    if imported_count % 100 == 0:
                        db.commit()
                        print(f"  已导入 {imported_count} 条...")
                except Exception as e:
                    error_count += 1
                    print(f"  第 {row_num} 行导入失败: {e}")
                    db.rollback()

            # 提交剩余记录
            db.commit()

        print(f"\n导入完成:")
        print(f"  成功导入: {imported_count} 条")
        print(f"  跳过（已存在）: {skipped_count} 条")
        print(f"  失败: {error_count} 条")

    except Exception as e:
        db.rollback()
        print(f"导入失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_customers()
