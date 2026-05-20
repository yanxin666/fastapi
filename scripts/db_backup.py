"""
PostgreSQL 数据库备份脚本

将数据库备份到本地文件，上传到腾讯云 COS，并自动清理超过 15 个的旧备份。

使用方式：
    .venv/Scripts/python.exe scripts/db_backup.py

备份文件：
    - 格式：pg_dump 自定义压缩格式（-Fc），标准扩展名 .dump
    - 存储位置：tmp/db/YYYYMMDD.dump
    - 恢复方式：pg_restore -h host -U user -d dbname file.dump
    - COS 路径：dbBack/YYYYMMDD.dump

注意事项：
    - 需要 pg_dump 在系统 PATH 中可用
    - 需要 .env 中配置 APP_DATABASE_URL 和腾讯云 COS 密钥
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

# 将项目根目录加入 sys.path，以便导入 app 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.integrations.cos.schemas import DeleteFileSchema, InitClientSchema, UploadFileSchema
from app.integrations.cos.service import COSService

# 常量配置
COS_REGION = "ap-beijing"
COS_BUCKET = "crm-1256276789"
COS_BACKUP_PREFIX = "dbBack/"
LOCAL_BACKUP_DIR = PROJECT_ROOT / "tmp" / "db"
MAX_BACKUP_FILES = 15


def parse_database_url(database_url: str) -> dict:
    """
    解析 PostgreSQL 连接字符串，提取连接参数。

    支持格式：postgresql+psycopg://user:pass@host:port/dbname
    会自动去除 +psycopg 后缀，因为 pg_dump 不识别该驱动标识。
    """
    # 去除 SQLAlchemy 驱动标识，例如 postgresql+psycopg:// → postgresql://
    if "+" in database_url:
        scheme, rest = database_url.split("://", 1)
        driverless_scheme = scheme.split("+")[0]
        database_url = f"{driverless_scheme}://{rest}"

    parsed = urlparse(database_url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "dbname": parsed.path.lstrip("/"),
    }


def run_pg_dump(db_params: dict, output_path: Path) -> None:
    """
    执行 pg_dump 命令生成数据库备份文件。

    使用 -Fc 选项生成自定义格式备份（压缩），恢复时使用 pg_restore。
    所有连接参数通过 PostgreSQL 标准环境变量传递，避免命令行暴露敏感信息。
    --no-password 确保认证失败时立即报错，而非挂住等待交互输入。
    """
    # 构建环境变量：使用 PostgreSQL 标准连接参数环境变量
    env = os.environ.copy()
    env["PGHOST"] = str(db_params["host"])
    env["PGPORT"] = str(db_params["port"])
    env["PGUSER"] = db_params["user"]
    env["PGDATABASE"] = db_params["dbname"]
    env["PGPASSWORD"] = db_params["password"]

    cmd = [
        "pg_dump",
        "-Fc",
        "--no-password",
        "-f", str(output_path),
    ]

    print(f"正在执行 pg_dump 备份数据库: {db_params['dbname']}@{db_params['host']}:{db_params['port']}")

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip() or "未知错误"
        raise RuntimeError(f"pg_dump 执行失败（返回码 {result.returncode}）: {error_msg}")

    # 确保备份文件已生成且非空
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("pg_dump 执行完成但备份文件为空或不存在")

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"数据库备份完成，文件大小: {file_size_mb:.2f} MB")


def get_cos_service() -> COSService:
    """创建 COSService 实例，使用应用配置中的腾讯云密钥。"""
    settings = get_settings()
    init_params = InitClientSchema(
        region=COS_REGION,
        secret_id=settings.tencent_cos_secret_id,
        secret_key=settings.tencent_cos_secret_key,
        token=None,
        scheme="https",
    )
    return COSService(init_params)


def upload_backup_to_cos(cos_service: COSService, local_path: Path, filename: str) -> None:
    """
    将备份文件上传到腾讯云 COS。

    COS 上的对象路径为: dbBack/{filename}
    """
    object_name = f"{COS_BACKUP_PREFIX}{filename}"
    print(f"正在上传备份文件到 COS: {object_name}")

    cos_service.upload_file(
        UploadFileSchema(
            bucket_name=COS_BUCKET,
            object_name=object_name,
            file_path=str(local_path),
        )
    )

    print(f"备份文件已上传到 COS: {object_name}")


def cleanup_old_backups(cos_service: COSService) -> None:
    """
    清理旧的备份文件，只保留最近 MAX_BACKUP_FILES 个。

    扫描本地 tmp/db/ 目录中的 .dump 文件，按文件名日期排序，
    超过上限的文件同时从本地和 COS 删除。
    YYYYMMDD.dump 格式的文件名，字典序即时间序，无需额外解析日期。
    """
    if not LOCAL_BACKUP_DIR.exists():
        return

    # 列出所有 .dump 文件，按文件名排序（YYYYMMDD 字典序即时间序）
    backup_files = sorted(
        [f for f in LOCAL_BACKUP_DIR.iterdir() if f.suffix == ".dump"],
        key=lambda f: f.name,
    )

    if len(backup_files) <= MAX_BACKUP_FILES:
        print(f"当前备份数量 {len(backup_files)}，未超过上限 {MAX_BACKUP_FILES}，无需清理")
        return

    # 需要删除的文件数量：最旧的排在前面
    delete_count = len(backup_files) - MAX_BACKUP_FILES
    files_to_delete = backup_files[:delete_count]

    print(f"当前备份数量 {len(backup_files)}，超过上限 {MAX_BACKUP_FILES}，需删除 {delete_count} 个旧备份")

    for file_path in files_to_delete:
        filename = file_path.name
        object_name = f"{COS_BACKUP_PREFIX}{filename}"

        # 先删除 COS 上的文件
        try:
            cos_service.delete_file(
                DeleteFileSchema(
                    bucket_name=COS_BUCKET,
                    object_name=object_name,
                )
            )
            print(f"已删除 COS 备份: {object_name}")
        except Exception as e:
            # COS 删除失败仍然继续删除本地文件，避免本地文件堆积
            print(f"删除 COS 备份失败: {object_name}，错误: {e}")

        # 再删除本地文件
        try:
            file_path.unlink()
            print(f"已删除本地备份: {file_path}")
        except Exception as e:
            print(f"删除本地备份失败: {file_path}，错误: {e}")


def main() -> None:
    """
    数据库备份主流程：
    1. 读取数据库连接配置
    2. 创建备份目录
    3. 执行 pg_dump 生成备份
    4. 上传到 COS
    5. 清理旧备份
    """
    print("=" * 50)
    print(f"数据库备份开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1. 读取配置
    settings = get_settings()
    if not settings.database_url:
        print("错误: 未配置数据库连接 URL（APP_DATABASE_URL）")
        sys.exit(1)

    db_params = parse_database_url(settings.database_url)

    # 2. 创建备份目录
    LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # 3. 生成备份文件名并执行 pg_dump
    today = datetime.now().strftime("%Y%m%d")
    backup_filename = f"{today}.dump"
    backup_path = LOCAL_BACKUP_DIR / backup_filename

    # 同一天重复运行时，先删除已有备份文件（覆盖备份）
    if backup_path.exists():
        backup_path.unlink()
        print(f"已删除今天的旧备份文件: {backup_path}")

    run_pg_dump(db_params, backup_path)

    # 4. 上传到 COS
    cos_service = get_cos_service()
    upload_backup_to_cos(cos_service, backup_path, backup_filename)

    # 5. 清理旧备份
    cleanup_old_backups(cos_service)

    print("=" * 50)
    print(f"数据库备份完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)


if __name__ == "__main__":
    main()
