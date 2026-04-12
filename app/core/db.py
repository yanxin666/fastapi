"""
数据库连接管理模块

这个模块负责：
1. 创建数据库引擎
2. 管理数据库会话
3. 提供依赖注入函数供 FastAPI 使用
"""

from functools import lru_cache
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

# 创建 SQLAlchemy 基类，所有数据模型都需要继承这个基类
Base = declarative_base()
"""
SQLAlchemy  declarative 基类

所有 ORM 数据模型都必须继承这个基类，
这样 SQLAlchemy 才能自动识别和映射这些类到数据库表。
"""


@lru_cache
def get_engine() -> Engine:
    """
    创建并返回数据库引擎（单例模式）

    数据库引擎是 SQLAlchemy 的核心组件，负责：
    1. 管理数据库连接池
    2. 处理 SQL 语句的执行
    3. 处理事务

    使用 lru_cache 确保整个应用只创建一个引擎实例。

    Returns:
        Engine: SQLAlchemy 数据库引擎对象
    """
    settings = get_settings()
    # 创建数据库引擎，pool_pre_ping=True 表示每次从连接池获取连接前先测试连接是否有效
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker:
    """
    创建并返回数据库会话工厂（单例模式）

    会话工厂用于创建数据库会话对象（Session）。
    使用 lru_cache 确保整个应用只创建一个会话工厂实例。

    Returns:
        sessionmaker: SQLAlchemy 会话工厂对象
    """
    # autocommit=False：不自动提交事务，需要手动调用 commit()
    # autoflush=False：不自动刷新会话到数据库，需要手动调用 flush()
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入函数：获取数据库会话

    这是一个生成器函数，用于在 FastAPI 路由中注入数据库会话。
    使用方式：
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...

    工作流程：
    1. 创建一个新的数据库会话
    2. 通过 yield 将会话提供给路由函数使用
    3. 路由函数执行完毕后，无论成功或失败，都会关闭会话

    Yields:
        Session: SQLAlchemy 数据库会话对象
    """
    # 从会话工厂创建一个新的数据库会话
    db = get_session_factory()()
    try:
        # yield 关键字将 db 会话提供给调用方使用
        # 调用方执行完后，会继续执行 finally 块
        yield db
    finally:
        # 确保会话一定会被关闭，防止连接泄漏
        db.close()
