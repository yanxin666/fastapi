"""
安全相关工具模块

这个模块提供了以下安全功能：
1. 密码哈希和验证
2. JWT token 的创建和解析
3. 访问令牌和刷新令牌的管理
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings


class InvalidTokenError(ValueError):
    """
    无效 token 异常

    当 token 解析失败或验证失败时抛出此异常
    """

    pass


@dataclass(slots=True)
class TokenPayload:
    """
    JWT token 的有效载荷数据类

    用于存储从 JWT token 中解析出的数据。

    Attributes:
        subject: 主题，通常是用户 ID
        token_type: token 类型，"access" 或 "refresh"
        expires_at: token 过期时间
        token_id: token 唯一标识（仅刷新令牌有）
    """

    subject: str
    token_type: str
    expires_at: datetime
    token_id: str | None = None


def hash_password(password: str) -> str:
    """
    密码哈希函数

    使用 PBKDF2-HMAC-SHA256 算法对密码进行哈希处理。
    每次哈希都会生成一个新的随机盐值，确保相同的密码也会得到不同的哈希值。

    为什么需要盐值？
    - 防止彩虹表攻击
    - 即使两个用户使用相同的密码，他们的哈希值也不同

    Args:
        password: 原始密码字符串

    Returns:
        str: 哈希后的密码，格式为 "盐值$哈希值"
    """
    # 生成一个 16 字节的随机盐值，转换为十六进制字符串（32个字符）
    salt = secrets.token_hex(16)

    # 使用 PBKDF2 算法进行密码哈希
    # 参数说明：
    # - sha256: 使用的哈希算法
    # - password.encode("utf-8"): 将密码编码为字节
    # - salt.encode("utf-8"): 将盐值编码为字节
    # - 100000: 迭代次数，次数越多越安全但也越慢
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )

    # 将盐值和哈希值组合在一起存储，用 $ 分隔
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    验证密码是否正确

    将输入的密码使用相同的盐值和算法进行哈希，
    然后与存储的哈希值进行比较。

    Args:
        password: 用户输入的原始密码
        password_hash: 存储的哈希密码（格式："盐值$哈希值"）

    Returns:
        bool: 密码正确返回 True，否则返回 False
    """
    try:
        # 从存储的哈希值中分离出盐值和期望的哈希值
        salt, expected_digest = password_hash.split("$", maxsplit=1)
    except ValueError:
        # 如果格式不对，直接返回验证失败
        return False

    # 使用相同的盐值和算法对输入的密码进行哈希
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    ).hex()

    # 使用 hmac.compare_digest 进行比较，防止时序攻击
    # 为什么不用 == ?
    # 普通的 == 比较会在遇到第一个不相等的字符时就返回，
    # 攻击者可以通过测量响应时间来逐位猜测密码哈希值
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(subject: str) -> str:
    """
    创建访问令牌（Access Token）

    访问令牌用于 API 请求认证，有效期较短（默认 30 分钟）。
    客户端应该在访问令牌过期前使用刷新令牌获取新的访问令牌。

    Args:
        subject: 主题，通常是用户 ID（字符串格式）

    Returns:
        str: 编码后的 JWT 访问令牌
    """
    settings = get_settings()

    # 计算过期时间：当前时间 + 配置的有效期
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_ttl_minutes
    )

    # 调用内部函数编码 token
    return _encode_token(subject=subject, token_type="access", expires_at=expires_at)


def create_refresh_token(subject: str, token_id: str) -> str:
    """
    创建刷新令牌（Refresh Token）

    刷新令牌用于获取新的访问令牌，有效期较长（默认 7 天）。
    刷新令牌会存储在数据库中，可以被撤销。

    Args:
        subject: 主题，通常是用户 ID（字符串格式）
        token_id: 令牌唯一标识，用于在数据库中跟踪和撤销令牌

    Returns:
        str: 编码后的 JWT 刷新令牌
    """
    settings = get_settings()

    # 计算过期时间：当前时间 + 配置的有效期
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)

    # 调用内部函数编码 token，传入 token_id
    return _encode_token(
        subject=subject,
        token_type="refresh",
        expires_at=expires_at,
        token_id=token_id,
    )


def decode_token(token: str, *, expected_token_type: str) -> TokenPayload:
    """
    解码并验证 JWT token

    验证内容包括：
    1. 签名是否正确
    2. 是否已过期
    3. token 类型是否符合预期

    Args:
        token: JWT token 字符串
        expected_token_type: 期望的 token 类型，"access" 或 "refresh"

    Returns:
        TokenPayload: 解析后的 token 数据

    Raises:
        InvalidTokenError: 当 token 无效、类型不匹配或过期时抛出
    """
    settings = get_settings()

    try:
        # 使用 jwt.decode 解析和验证 token
        # 会自动验证签名和过期时间
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.InvalidTokenError as exc:
        # token 无效（签名错误、格式错误、已过期等）
        raise InvalidTokenError("Invalid token") from exc

    # 验证 token 类型是否符合预期
    token_type = payload.get("type")
    if token_type != expected_token_type:
        raise InvalidTokenError("Unexpected token type")

    # 获取主题（用户 ID）
    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token subject is required")

    # 从 payload 中获取过期时间戳，转换为 datetime 对象
    expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)

    # 返回解析后的数据对象
    return TokenPayload(
        subject=subject,
        token_type=token_type,
        expires_at=expires_at,
        token_id=payload.get("jti"),
    )


def _encode_token(
    *,
    subject: str,
    token_type: str,
    expires_at: datetime,
    token_id: str | None = None,
) -> str:
    """
    内部函数：编码 JWT token

    这是一个私有辅助函数，不应该被外部模块直接调用。
    使用 * 作为第一个参数，表示后面的参数都必须使用关键字参数传递。

    Args:
        subject: 主题，通常是用户 ID
        token_type: token 类型，"access" 或 "refresh"
        expires_at: 过期时间
        token_id: 可选，令牌唯一标识

    Returns:
        str: 编码后的 JWT token
    """
    settings = get_settings()

    # 构建 JWT payload（有效载荷）
    payload = {
        "sub": subject,
        # subject：主题，标准 JWT 字段，这里存储用户 ID
        "type": token_type,
        # 自定义字段：token 类型
        "exp": expires_at,
        # expiration time：过期时间，标准 JWT 字段，Unix 时间戳格式
    }

    # 如果提供了 token_id，则添加到 payload 中
    if token_id is not None:
        payload["jti"] = token_id
        # JWT ID：令牌唯一标识，标准 JWT 字段

    # 使用 jwt.encode 编码生成 token
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
