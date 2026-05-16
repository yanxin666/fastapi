import logging
import sys
from threading import Lock
from typing import Any

from qcloud_cos import CosConfig, CosS3Client

# 配置日志输出到控制台。
# 默认 INFO：看到关键运行信息；排查问题时可改成 DEBUG。
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

"""
# 下面是官方示例（注释块），展示如何直接创建客户端。
# 项目里改成了 _get_client() 懒加载单例方式，更适合实际项目复用。
# secret_id = os.environ['COS_SECRET_ID']
# secret_key = os.environ['COS_SECRET_KEY']
# region = 'ap-beijing'
# token = None
# scheme = 'https'
# config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
# client = CosS3Client(config)
"""

# 全局客户端实例缓存：
# 第一次创建后保存到这里，后续直接复用，避免重复初始化。
_client_instance: Any = None

# 线程锁：
# 多线程同时调用 _get_client() 时，保证同一时刻只有一个线程执行创建逻辑。
_client_lock = Lock()


def _get_client(
    region: str,
    secret_id: str,
    secret_key: str,
    token: str | None = None,
    scheme: str = "https",
):
    """
    获取 COS 客户端（单例模式，进程内只初始化一次）。

    参数:
        region: COS 地域，例如 ap-guangzhou
        secret_id: 腾讯云密钥 ID
        secret_key: 腾讯云密钥 Key
        token: 临时密钥场景下的 token（长期密钥可不传）
        scheme: 协议，默认 https

    返回:
        CosS3Client: 已初始化的 COS 客户端实例
    """
    global _client_instance

    # 第一层判断：大多数情况下已经初始化，直接返回，速度快。
    if _client_instance is None:
        # 进入锁，防止并发场景重复创建多个 client。
        with _client_lock:
            # 第二层判断（双重检查）：
            # 可能另一个线程在你拿到锁前已经创建好了，所以要再判断一次。
            if _client_instance is None:
                # 创建 SDK 配置对象
                config = CosConfig(
                    Region=region,
                    SecretId=secret_id,
                    SecretKey=secret_key,
                    Token=token,
                    Scheme=scheme,
                )
                # 真正创建客户端，只会执行一次
                _client_instance = CosS3Client(config)

    # 返回全局缓存的客户端实例
    return _client_instance
