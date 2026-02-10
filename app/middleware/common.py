import time

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.examples.request_context_demo import RequestContext, request_ctx_var
from fastapi import HTTPException, Request


# CORS 中间件配置
def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# 请求时间中间件
def setup_process_time_middleware(app):
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


# 全局异常处理器
def setup_http_exception_handler(app):
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.detail, "error": True},
        )


# 记录 API 入参和出参的中间件
def setup_logging_middleware(app):
    @app.middleware("http")
    async def log_request_response(request: Request, call_next):
        # 记录请求信息
        print(f"Incoming request: {request.method} {request.url}")
        print(f"Request headers: {request.headers}")
        if request.method in ["POST", "PUT", "PATCH"]:
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
    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):
        """
        HTTP 中间件：
        - 在 call_next 前：请求尚未处理
        - 在 call_next 后：请求已完成（可读取最终 Context）
        """
        start = time.time()

        # 进入下游（路由匹配 + Depends + endpoint）
        response = await call_next(request)

        cost_ms = int((time.time() - start) * 1000)

        # 从 request.state 中读取 Context（推荐方式）
        ctx: RequestContext | None = getattr(request.state, "ctx", None)

        # 同时尝试从 ContextVar 读取（演示用）
        ctx_from_var = request_ctx_var.get()

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
