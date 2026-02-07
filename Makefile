# Makefile for fastapi project

# 安装依赖包，并将安装的包写入 requirements.txt 文件，以便其他人可以通过 requirements.txt 文件安装相同的依赖包，确保项目环境的一致性。
# 这里使用了清华大学的 PyPI 镜像源，可以加快安装速度，特别是在国内网络环境下。
install:
	.venv/bin/pip install $(filter-out $@,$(MAKECMDGOALS)) -i https://pypi.tuna.tsinghua.edu.cn/simple
	.venv/bin/pip freeze > requirements.txt
%:
	@:

# 其他常用命令可以继续添加
