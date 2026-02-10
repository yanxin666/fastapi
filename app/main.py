import pathlib  # 导入路径库

from fastapi import FastAPI  # 导入 FastAPI 框架

from app.init import auto_register_routers  # 导入自动注册 router 的函数
from app.middleware import common as middleware_main  # 导入中间件注册模块

# 创建 FastAPI 应用实例
app = FastAPI()

# 注册中间件
middleware_main.setup_cors(app)  # 跨域中间件
middleware_main.setup_process_time_middleware(app)  # 请求时间中间件
middleware_main.setup_http_exception_handler(app)  # 全局异常处理器
middleware_main.setup_logging_middleware(app)  # 请求日志中间件
middleware_main.setup_audit_middleware(app)  # 审计中间件

# 启动时递归注册 app/api 及其所有子包下的 router
api_pkg = "app.api"  # 指定 API 包名
api_path = pathlib.Path(__file__).parent / "api"  # 获取 api 目录的绝对路径
auto_register_routers(app, api_pkg, api_path)  # 调用函数自动注册 router
