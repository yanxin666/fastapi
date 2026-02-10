import importlib  # 导入动态模块加载库
import pathlib  # 导入路径库
import pkgutil  # 导入包工具库，用于遍历模块

from fastapi import FastAPI  # 导入 FastAPI 类型


# 定义一个函数，递归遍历指定包路径下的所有模块和子包，自动导入并注册 router
def auto_register_routers(app: FastAPI, pkg_name: str, pkg_path: pathlib.Path):
    """
    递归遍历 pkg_path 目录下所有模块和子包，自动导入并注册 router
    :param app: FastAPI 应用实例
    :param pkg_name: 包名字符串（如 'app.api'）
    :param pkg_path: 包路径对象
    """
    for finder, module_name, is_pkg in pkgutil.iter_modules(
        [str(pkg_path)]
    ):  # 遍历当前目录下所有模块和包
        full_module_name = f"{pkg_name}.{module_name}"
        if is_pkg:
            # 如果是子包，递归处理
            sub_pkg_path = pkg_path / module_name
            auto_register_routers(app, full_module_name, sub_pkg_path)
        else:
            # 如果是模块，动态导入并注册 router
            module = importlib.import_module(full_module_name)
            if hasattr(module, "router"):
                app.include_router(module.router)
