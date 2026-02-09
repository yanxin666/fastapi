from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import time

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
