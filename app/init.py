"""
应用初始化模块

提供自动注册路由的功能，递归扫描指定包目录下的所有模块，
自动导入并注册 router。
"""

import importlib  # 导入动态模块加载库
import pathlib  # 导入路径库
import pkgutil  # 导入包工具库，用于遍历模块

from fastapi import FastAPI  # 导入 FastAPI 类型


# 定义一个函数，递归遍历指定包路径下的所有模块和子包，自动导入并注册 router
def auto_register_routers(app: FastAPI, pkg_name: str, pkg_path: pathlib.Path):
    """
    递归遍历 pkg_path 目录下所有模块和子包，自动导入并注册 router

    工作流程：
    1. 遍历指定目录下的所有模块和子包
    2. 如果是子包，递归处理
    3. 如果是模块，动态导入该模块
    4. 检查模块是否导出了 router 属性
    5. 如果有 router，将其注册到 FastAPI 应用中
    6. 如果模块定义了 router_prefix_setting，使用配置中的前缀

    Args:
        app: FastAPI 应用实例
        pkg_name: 包名字符串（如 'app.api'）
        pkg_path: 包路径对象
    """
    # 遍历当前目录下所有模块和包
    for finder, module_name, is_pkg in pkgutil.iter_modules([str(pkg_path)]):
        # 构建完整的模块名，例如 'app.api.auth.auth'
        full_module_name = f"{pkg_name}.{module_name}"

        if is_pkg:
            # 如果是子包，递归处理
            sub_pkg_path = pkg_path / module_name
            auto_register_routers(app, full_module_name, sub_pkg_path)
        else:
            # 如果是模块，动态导入并注册 router
            # 使用 importlib 动态导入模块
            module = importlib.import_module(full_module_name)

            # 检查模块是否有 router 属性
            if hasattr(module, "router"):
                # 准备 include_kwargs 字典，用于传递给 app.include_router
                include_kwargs = {}

                # 获取应用的 settings
                settings = getattr(app.state, "settings", None)

                # 检查模块是否定义了 router_prefix_setting
                # router_prefix_setting 是一个字符串，指向 settings 中的属性名
                prefix_setting_name = getattr(module, "router_prefix_setting", None)

                # 如果 settings 和 prefix_setting_name 都存在，
                # 从 settings 中获取对应的前缀并添加到 include_kwargs 中
                if settings is not None and prefix_setting_name:
                    include_kwargs["prefix"] = getattr(settings, prefix_setting_name)

                # 注册 router 到 FastAPI 应用
                app.include_router(module.router, **include_kwargs)
