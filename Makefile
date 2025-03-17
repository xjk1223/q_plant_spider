.PHONY: install test lint format run build up down clean help

# 变量定义
PYTHON = python3
PIP = $(PYTHON) -m pip
PYTEST = $(PYTHON) -m pytest
FLAKE8 = $(PYTHON) -m flake8
BLACK = $(PYTHON) -m black
MYPY = $(PYTHON) -m mypy
VENV = venv
DOCKER = docker
DOCKER_COMPOSE = docker-compose
PROJECT_NAME = q_plant_spider

# 帮助命令
help:
	@echo "使用方法:"
	@echo "  make install        安装所有依赖"
	@echo "  make dev-install    安装开发依赖"
	@echo "  make test           运行测试"
	@echo "  make lint           运行代码检查"
	@echo "  make format         格式化代码"
	@echo "  make run            运行应用"
	@echo "  make build          构建Docker镜像"
	@echo "  make up             启动Docker容器"
	@echo "  make down           停止Docker容器"
	@echo "  make clean          清理临时文件"

# 安装依赖
install:
	$(PIP) install -r requirements/base.txt

dev-install:
	$(PIP) install -r requirements/dev.txt

# 测试
test:
	$(PYTEST) tests/ --cov=src/ --cov-report=term-missing

# 代码质量
lint:
	$(FLAKE8) src/ tests/
	$(MYPY) src/

format:
	$(BLACK) src/ tests/

# 运行
run:
	$(PYTHON) -m src.q_plant_spider.main

# Docker操作
build:
	$(DOCKER) build -t $(PROJECT_NAME) .

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

# 清理
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf downloaded_images
	rm -rf *.log
	find . -type d -name __pycache__ -exec rm -rf {} + 