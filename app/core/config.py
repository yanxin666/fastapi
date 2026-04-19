"""
应用配置管理模块

这个模块负责加载和管理应用的所有配置项。
配置可以通过环境变量或 .env 文件进行覆盖。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 基于当前文件计算项目根目录，避免从 tests 等子目录启动时找不到 .env
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    应用配置类

    使用 Pydantic 的 BaseSettings 来管理配置，
    支持从环境变量和 .env 文件读取配置。

    所有配置项都有默认值，生产环境请务必修改敏感配置（如 jwt_secret_key）
    """

    # 应用基本信息配置
    app_name: str = Field(default="FastAPI Service")
    """应用名称，用于标识和展示"""

    app_env: str = Field(default="development")
    """运行环境：development（开发）、production（生产）、testing（测试）"""

    app_version: str = Field(default="0.1.0")
    """应用版本号"""

    # API 路由配置
    api_v1_prefix: str = Field(default="/api/v1")
    """API v1 版本的路由前缀"""

    # 数据库连接配置
    database_url: str = Field(default="")
    """
    数据库连接 URL
    格式：postgresql+psycopg://用户名:密码@主机:端口/数据库名
    """

    # JWT 认证配置
    jwt_secret_key: str = Field(default="")
    """
    JWT 签名密钥，用于生成和验证 token
    生产环境必须使用强随机字符串并妥善保管
    """

    jwt_algorithm: str = Field(default="HS256")
    """JWT 签名算法，默认使用 HS256"""

    access_token_ttl_minutes: int = Field(default=30)
    """访问令牌（access token）的有效期，单位：分钟"""

    refresh_token_ttl_days: int = Field(default=7)
    """刷新令牌（refresh token）的有效期，单位：天"""

    # 腾讯云相关配置
    tencent_main_account_id: str = Field(default="100004453623")
    """腾讯云主账号 ID"""

    tencent_cos_user_name: str = Field(default="cos")
    """腾讯云 COS 用户名"""

    tencent_cos_secret_id: str = Field(default="")
    """腾讯云 COS SecretId"""

    tencent_cos_secret_key: str = Field(default="")
    """腾讯云 COS SecretKey"""

    # Pydantic 配置类，用于控制 Settings 的行为
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        # 环境变量前缀，只有以 APP_ 开头的环境变量才会被读取
        env_file=_ENV_FILE,
        # 固定使用项目根目录下的 .env，避免受当前工作目录影响
        env_file_encoding="utf-8",
        # .env 文件的编码格式
        case_sensitive=False,
        # 环境变量不区分大小写
        extra="ignore",
        # 忽略未定义的配置项
    )

    @property
    def admin_api_prefix(self) -> str:
        """
        后台管理 API 的路由前缀

        返回值示例：/api/v1/admin
        """
        return f"{self.api_v1_prefix}/admin"


@lru_cache
def get_settings() -> Settings:
    """
    获取应用配置实例（单例模式）

    使用 lru_cache 装饰器确保只创建一个 Settings 实例，
    避免重复读取配置文件，提高性能。

    Returns:
        Settings: 应用配置对象
    """
    return Settings()
