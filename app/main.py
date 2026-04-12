"""
FastAPI 应用入口模块

这是整个应用的主入口文件，负责：
1. 创建 FastAPI 应用实例
2. 配置中间件
3. 自动注册路由
4. 托管前端静态文件
"""

import pathlib

from app.core.config import get_settings
from app.init import auto_register_routers
from app.middleware import common as middleware_main
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 前端构建产物目录路径
# __file__ 是当前文件的路径，resolve() 得到绝对路径
# parent.parent 表示向上两级目录（app/main.py → app/ → 项目根目录）
FRONTEND_DIST_DIR = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dist"
"""前端构建产物目录路径"""

FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"
"""前端 SPA 入口文件 index.html 的路径"""


def setup_frontend(app: FastAPI) -> None:
    """
    设置前端静态文件托管

    当前端构建产物存在时（frontend/dist 目录），配置 FastAPI 来托管：
    1. /assets 目录下的静态资源
    2. /favicon.svg 网站图标
    3. SPA 的 index.html 入口文件
    4. SPA 路由回退（所有非 API 路径都返回 index.html）

    Args:
        app: FastAPI 应用实例
    """
    # 检查前端入口文件是否存在，如果不存在则不设置前端托管
    if not FRONTEND_INDEX_FILE.exists():
        return

    # 挂载 /assets 静态资源目录
    # 前端构建后的 JS、CSS、图片等资源通常放在 assets 目录下
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    # 处理 favicon.svg 网站图标
    favicon_file = FRONTEND_DIST_DIR / "favicon.svg"
    if favicon_file.exists():

        @app.get("/favicon.svg", include_in_schema=False)
        def frontend_favicon() -> FileResponse:
            """返回网站图标"""
            return FileResponse(favicon_file)

    # 处理根路径 /，返回前端 SPA 入口页面
    @app.get("/", include_in_schema=False)
    def frontend_index() -> FileResponse:
        """返回前端 SPA 首页"""
        return FileResponse(FRONTEND_INDEX_FILE)

    # SPA 路由回退处理
    # 对于单页应用（SPA），前端有自己的路由系统
    # 当用户直接访问 /users、/roles 等路径时，需要返回 index.html
    # 然后由前端路由接管并渲染对应的页面
    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_spa_fallback(full_path: str) -> FileResponse:
        """
        SPA 路由回退

        Args:
            full_path: 请求的完整路径

        Returns:
            FileResponse: 前端 index.html 文件

        Raises:
            HTTPException: 404 如果是 API 路径
        """
        # 如果是 API 路径（以 api/ 开头），返回 404
        # API 路径应该由后端路由处理，不应该走到这里
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        # 对于其他路径，都返回 index.html，让前端路由处理
        return FileResponse(FRONTEND_INDEX_FILE)


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例

    这是一个工厂函数，负责：
    1. 加载配置
    2. 创建 FastAPI 应用
    3. 设置中间件
    4. 自动注册路由
    5. 设置前端托管

    Returns:
        FastAPI: 配置好的 FastAPI 应用实例
    """
    # 获取应用配置
    settings = get_settings()

    # 创建 FastAPI 应用实例
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    # 将 settings 存储到 app.state 中，方便其他地方访问
    app.state.settings = settings

    # 设置各种中间件
    middleware_main.setup_cors(app)
    """设置 CORS 跨域中间件"""

    middleware_main.setup_process_time_middleware(app)
    """设置请求处理时间计时中间件"""

    middleware_main.setup_http_exception_handler(app)
    """设置全局 HTTP 异常处理器"""

    middleware_main.setup_logging_middleware(app)
    """设置请求/响应日志中间件"""

    middleware_main.setup_audit_middleware(app)
    """设置审计日志中间件"""

    # 自动注册 API 路由
    # 递归扫描 app/api 目录下的所有模块，自动注册 router
    api_pkg = "app.api"
    """API 包名"""

    api_path = pathlib.Path(__file__).parent / "api"
    """API 包路径"""

    auto_register_routers(app, api_pkg, api_path)

    # 设置前端托管
    setup_frontend(app)

    # 返回配置好的应用实例
    return app


# 创建全局的 FastAPI 应用实例
# 这是 uvicorn 等 ASGI 服务器会加载的实例
# 启动命令示例：uvicorn app.main:app --reload
app = create_app()
