"""
通用中间件模块

提供了各种通用的中间件和异常处理器：
1. CORS 跨域配置
2. 请求处理时间计时
3. 全局异常处理
4. 请求/响应日志记录
5. 审计日志中间件
"""

import time

from app.examples.request_context_demo import RequestContext, request_ctx_var
from fastapi import HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# CORS 中间件配置
def setup_cors(app):
    """
    配置 CORS（跨域资源共享）中间件

    CORS 允许浏览器在不同域名下的前端应用访问后端 API。

    注意：当前配置允许所有来源、所有方法、所有头部，
    这在开发环境很方便，但生产环境应该根据实际需求限制。

    Args:
        app: FastAPI 应用实例
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        # 允许的来源（域名），["*"] 表示允许所有来源
        allow_credentials=True,
        # 是否允许携带凭证（如 Cookie、Authorization 头）
        allow_methods=["*"],
        # 允许的 HTTP 方法，["*"] 表示允许所有方法
        allow_headers=["*"],
        # 允许的请求头，["*"] 表示允许所有头部
    )


# 请求时间中间件
def setup_process_time_middleware(app):
    """
    配置请求处理时间计时中间件

    在响应头中添加 X-Process-Time，记录请求处理耗时（秒）。

    Args:
        app: FastAPI 应用实例
    """

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """
        实际的中间件函数

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        # 记录请求开始时间
        start_time = time.time()

        # 调用下一个中间件或路由处理函数，获取响应
        response = await call_next(request)

        # 计算处理耗时
        process_time = time.time() - start_time

        # 将耗时添加到响应头
        response.headers["X-Process-Time"] = str(process_time)

        return response


# 全局异常处理器
def setup_http_exception_handler(app):
    """
    配置全局 HTTP 异常处理器

    统一处理 HTTPException，返回标准化的 JSON 响应格式。

    Args:
        app: FastAPI 应用实例
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """
        HTTPException 异常处理函数

        Args:
            request: 请求对象
            exc: HTTPException 异常对象

        Returns:
            JSONResponse: 标准化的 JSON 响应
        """
        return JSONResponse(
            status_code=exc.status_code,
            # HTTP 状态码
            content={"message": exc.detail, "error": True},
            # 响应内容，包含错误消息和错误标识
            # 格式：{"message": "错误详情", "error": true}
        )


# 记录 API 入参和出参的中间件
def setup_logging_middleware(app):
    """
    配置请求/响应日志中间件

    记录请求和响应的详细信息，用于调试。

    注意：生产环境应该使用专业的日志库（如 logging）
    而不是 print，并且要注意避免记录敏感信息。

    Args:
        app: FastAPI 应用实例
    """

    @app.middleware("http")
    async def log_request_response(request: Request, call_next):
        """
        实际的日志中间件函数

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        # 记录请求信息
        print(f"Incoming request: {request.method} {request.url}")
        print(f"Request headers: {request.headers}")

        # 对于 POST、PUT、PATCH 请求，记录请求体
        if request.method in ["POST", "PUT", "PATCH"]:
            # 注意：await request.body() 会消费请求体，
            # 实际使用时需要特殊处理，避免影响后续读取
            body = await request.body()
            print(f"Request body: {body.decode('utf-8')}")

        # 处理请求并获取响应
        response = await call_next(request)

        # 记录响应信息
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")

        return response


# ============================================================
# 五、HTTP Middleware：审计 / 日志 / 横切关注点
# ============================================================
def setup_audit_middleware(app):
    """
    配置审计日志中间件

    记录请求的审计信息，包括：
    - 请求路径和方法
    - 响应状态码
    - 处理耗时
    - 请求上下文信息

    这是一个示例中间件，展示如何使用 request.state 和 ContextVar。

    Args:
        app: FastAPI 应用实例
    """

    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):
        """
        实际的审计中间件函数

        HTTP 中间件的执行流程：
        1. 在 call_next 前：请求尚未处理，可以做前置操作
        2. 调用 call_next：进入下游（路由匹配 + Depends + endpoint）
        3. 在 call_next 后：请求已完成，可以读取最终响应和 Context

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        # 记录请求开始时间
        start = time.time()

        # 进入下游处理（路由匹配 + 依赖注入 + 端点执行）
        response = await call_next(request)

        # 计算处理耗时（毫秒）
        cost_ms = int((time.time() - start) * 1000)

        # 从 request.state 中读取 Context（推荐方式）
        # request.state 是 FastAPI 提供的用于存储请求上下文的对象
        ctx: RequestContext | None = getattr(request.state, "ctx", None)

        # 同时尝试从 ContextVar 读取（演示用）
        # ContextVar 是 Python 标准库提供的上下文变量
        ctx_from_var = request_ctx_var.get()

        # 打印审计日志
        print("=== AUDIT LOG ===")
        print(
            {
                "path": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "cost_ms": cost_ms,
                "ctx_from_request_state": ctx,
                "ctx_from_contextvar": ctx_from_var,
            }
        )

        return response
