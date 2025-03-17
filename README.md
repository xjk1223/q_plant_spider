# Q-Plant Spider

![版本](https://img.shields.io/badge/版本-1.0.0-blue.svg)
![许可](https://img.shields.io/badge/许可-MIT-green.svg)
![Python版本](https://img.shields.io/badge/Python-3.8%2B-blue)

Q-Plant Spider 是一个自动化数据采集和上传工具，用于从NIO Q-Plant系统抓取问题数据并将其上传到飞书多维表格。该工具通过飞书机器人提供用户交互界面，支持按条件查询和批量更新数据。

## ✨ 功能特性

- 自动登录NIO Q-Plant系统获取数据
- 支持按PVBR号、时间范围和车型筛选数据
- 自动提取问题详情和相关图片
- 将数据实时同步到飞书多维表格
- 通过飞书机器人提供交互式查询和更新界面
- 自动处理图片下载和上传到飞书
- 完善的错误处理和重试机制
- 支持Docker容器化部署

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Microsoft Edge浏览器 (用于自动化登录)
- 飞书开放平台应用
- Docker (可选，用于容器化部署)

### 安装

1. 克隆仓库:

```bash
git clone https://github.com/xjk1223/q-plant-spider.git
cd q-plant-spider
```

2. 安装依赖:

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
make install
```

3. 配置环境变量:

创建`.env`文件并配置以下环境变量:

```
# NIO账号
NIO_USERNAME=your_username
NIO_PASSWORD=your_password

# 飞书应用
APP_ID=your_app_id
APP_SECRET=your_app_secret
ENCRYPT_KEY=your_encrypt_key
VERIFICATION_TOKEN=your_verification_token

# 飞书多维表格
APP_TOKEN=your_app_token
TABLE_ID=your_table_id
RESPONSE_TEMPLATE_ID=your_response_template_id
RESULT_TEMPLATE_ID=your_result_template_id

# 配置
BATCH_SIZE=990
PAGE_SIZE=500
```

### 运行

```bash
make run
```

### 详细运行说明

#### Windows 环境（推荐）
```powershell
# 方式1：直接运行（推荐）
python -m src.q_plant_spider.main

# 方式2：后台运行
Start-Process python -ArgumentList "-m src.q_plant_spider.main" -WindowStyle Hidden

# 方式3：开发模式（热重载）
python -m scripts.run_with_reload

# 查看日志
Get-Content -Path "logs/app_*.log" -Wait

# 停止服务
Get-Process python | Where-Object {$_.MainWindowTitle -eq ""} | Stop-Process
```

#### Linux 环境（可选）
```bash
# 直接运行
python -m src.q_plant_spider.main

# 后台运行
nohup python -m src.q_plant_spider.main > output.log 2>&1 &

# 开发模式（热重载）
python -m scripts.run_with_reload

# 查看运行状态
tail -f output.log

# 停止服务
ps aux | grep "python -m src.q_plant_spider.main"
kill -9 <进程ID>
```

## 🐳 Docker部署

1. 构建镜像:

```bash
make build
```

2. 启动容器:

```bash
make up
```

3. 停止容器:

```bash
make down
```

## 🧪 测试

```bash
make test
```

## 🔧 开发

```bash
# 安装开发依赖
make dev-install

# 代码格式化
make format

# 代码检查
make lint

# 开发模式运行（带热重载）
python -m scripts.run_with_reload
```

## 📁 项目结构

```
q-plant-spider/
├── src/                      # 源代码
│   └── q_plant_spider/       # 主包
│       ├── api/              # API客户端
│       │   ├── bitable_api.py    # 飞书多维表格API
│       │   ├── event_handlers.py # 事件处理器
│       │   └── lark_api.py       # 飞书API
│       ├── core/             # 核心功能
│       │   ├── auth.py           # 认证模块
│       │   ├── data_processor.py # 数据处理
│       │   ├── query.py          # 查询实现
│       │   └── services.py       # 业务服务
│       └── utils/            # 工具函数
│           ├── image_handler.py  # 图片处理
│           └── logger.py         # 日志配置
├── scripts/                  # 脚本工具
│   └── run_with_reload.py    # 热重载
├── tests/                    # 测试代码
├── requirements/             # 依赖文件
│   ├── base.txt              # 基础依赖
│   └── dev.txt               # 开发依赖
├── .github/workflows/        # CI/CD配置
├── .gitignore                # Git忽略文件
├── Dockerfile                # Docker构建文件
├── docker-compose.yml        # Docker Compose配置
├── Makefile                  # 常用命令
├── pyproject.toml            # 项目配置
└── README.md                 # 项目说明
```

## 🔑 核心模块

- **auth.py**: 负责与NIO系统认证，获取cookies
- **query.py**: 实现数据查询逻辑
- **data_processor.py**: 处理和转换数据
- **services.py**: 整合核心业务逻辑
- **image_handler.py**: 处理图片的下载和上传
- **event_handlers.py**: 处理飞书机器人事件
- **bitable_api.py**: 操作飞书多维表格
- **lark_api.py**: 与飞书API交互

## 🔄 工作流程

1. 用户通过飞书机器人发起查询请求
2. 系统使用存储的cookies访问Q-Plant系统（如cookies过期则自动重新登录）
3. 根据用户条件查询问题数据
4. 处理返回的数据，提取问题详情和图片
5. 将图片下载并上传到飞书
6. 将处理后的数据写入飞书多维表格
7. 返回查询和更新结果给用户

## 📊 应用场景

- 质量问题实时跟踪与分析
- 车型问题统计与报表生成
- 问题图片统一管理与共享
- 跨部门协作与问题处理

## 📃 许可证

本项目使用MIT许可证 - 详情请查看[LICENSE](LICENSE)文件

## 👥 贡献指南

欢迎贡献代码和提出问题！

1. Fork项目
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开Pull Request
