from fastapi import FastAPI # 导入 FastAPI 框架
import importlib  # 导入动态模块加载库
import pkgutil    # 导入包工具库，用于遍历模块
import pathlib    # 导入路径库
from app.middleware import main as middleware_main  # 导入中间件注册模块

# 创建 FastAPI 应用实例
app = FastAPI()

# 注册中间件和异常处理器
middleware_main.setup_cors(app)
middleware_main.setup_process_time_middleware(app)
middleware_main.setup_http_exception_handler(app)
middleware_main.setup_logging_middleware(app)

# 定义一个函数，递归遍历指定包路径下的所有模块和子包，自动导入并注册 router
def auto_register_routers(pkg_name: str, pkg_path: pathlib.Path):
    """
    递归遍历 pkg_path 目录下所有模块和子包，自动导入并注册 router
    :param pkg_name: 包名字符串（如 'app.api'）
    :param pkg_path: 包路径对象
    """
    for finder, module_name, is_pkg in pkgutil.iter_modules([str(pkg_path)]):  # 遍历当前目录下所有模块和包
        full_module_name = f"{pkg_name}.{module_name}"
        if is_pkg:
            # 如果是子包，递归处理
            sub_pkg_path = pkg_path / module_name
            auto_register_routers(full_module_name, sub_pkg_path)
        else:
            # 如果是模块，动态导入并注册 router
            module = importlib.import_module(full_module_name)
            if hasattr(module, 'router'):
                app.include_router(module.router)

# 启动时递归注册 app/api 及其所有子包下的 router
api_pkg = 'app.api'  # 指定 API 包名
api_path = pathlib.Path(__file__).parent / 'api'  # 获取 api 目录的绝对路径
auto_register_routers(api_pkg, api_path) # 调用函数自动注册 router
