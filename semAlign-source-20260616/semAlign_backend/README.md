# SemAlign Backend

基于 FastAPI 的企业级标准管理系统后端 API。

## 📋 项目特性

* ✅ **分层架构**：清晰的核心层、模型层、schemas 层和路由层
* ✅ **标准化响应**：统一的 API 响应格式
* ✅ **类型安全**：完整的 Pydantic 类型定义
* ✅ **依赖注入**：FastAPI 依赖注入管理数据库会话和用户认证
* ✅ **安全认证**：JWT Token 认证和权限控制

## 📁 项目结构

```text
semAlign_backend/
├── main.py                 # FastAPI 应用入口（路由注册、CORS、生命周期）
├── requirements.txt
├── .env.example
├── GAP_ANALYSIS.md         # 与 MVP 功能对照说明
├── README.md
├── core/                   # 核心基础设施
│   ├── config.py           # 配置（pydantic-settings）
│   ├── security.py       # JWT、密码哈希
│   ├── database.py       # 引擎、Session、Base
│   └── deps.py             # get_db、get_current_user 等依赖
├── models/                 # SQLAlchemy 模型
│   ├── base.py
│   ├── user.py
│   ├── standard.py
│   └── alignment_task.py
├── schemas/                # Pydantic 请求/响应模型
│   ├── base.py             # APIResponse 等统一封装
│   ├── user.py
│   ├── standard.py
│   ├── workbench.py
│   ├── import_.py          # 上传/导入响应（文件名避关键字 import）
│   ├── search.py
│   └── alignment.py
├── routers/                # HTTP 路由（均在 main.py 中以 prefix=/api 挂载）
│   ├── auth.py             # /api/auth/*
│   ├── user.py             # /api/user/*
│   ├── workbench.py        # /api/workbench/*
│   ├── standards.py        # /api/standards/*
│   ├── statistics.py     # /api/statistics
│   ├── standard_import.py  # /api/import/*
│   ├── search.py           # /api/search/*
│   ├── alignment.py        # /api/alignment/*
│   ├── comparison.py       # /api/comparison/*
│   ├── report_export.py  # /api/export/*
│   └── rules.py            # /api/rules/*
├── services/               # 业务服务（比对演示数据、规则编排、导出 Excel 等）
│   ├── conflict_detection/
│   ├── preprocessing/
│   ├── rule_engine/
│   ├── reporting/
│   ├── comparison_payloads.py
│   ├── export_report.py
│   └── rule_service.py
├── utils/                  # PDF/校验等工具
│   ├── pdf_parser.py
│   ├── validators.py
│   ├── validation.py
│   └── file_utils.py
└── scripts/                # 运维脚本
    ├── create_tables.py
    ├── init_user.py        # 初始化管理员
    └── update_password.py
```

（若引入 Alembic，可在项目根增加 `alembic/` 与迁移配置。）

## 🚀 快速开始

### 1. 环境要求

* Python 3.10+（建议 3.11 / 3.12，与 `numpy` 2.x、`pandas` 2.2+ 兼容）

* pip（随 Python 安装）

### 2. Python 虚拟环境（推荐）

在**独立虚拟环境**中安装依赖，可避免：

* macOS / Linux 上 **PEP 668**（`externally-managed-environment`）禁止向系统 Python 全局安装包；

* 与系统里已安装的 **opencv-python**、其它项目的 **numpy** 版本冲突。

在项目根目录 `semAlign_backend/` 下执行：

```bash
cd semAlign_backend

# 创建虚拟环境（目录名 .venv 已在 .gitignore 中忽略）
python3 -m venv .venv

# 激活：macOS / Linux
source .venv/bin/activate

# 激活：Windows CMD
# .venv\Scripts\activate.bat
# 激活：Windows PowerShell
# .venv\Scripts\Activate.ps1

# 建议：升级 pip 后再装依赖
python -m pip install -U pip
```

之后每次开发前，先 `cd` 到 `semAlign_backend` 并执行上述 `activate`，终端提示符前会出现 `(.venv)`。

退出虚拟环境：`deactivate`。

### 3. 安装依赖

**在已激活的虚拟环境中**执行：

```bash
cd semAlign_backend
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，配置必要的环境变量
# 必须配置的变量：
#   - SECRET_KEY: JWT 加密密钥（生产环境必须修改）
#   - DATABASE_URL: 数据库连接字符串
#   - CORS_ORIGINS: 允许跨域的源地址
```

**.env 文件示例：**

```bash
# ==================== 应用配置 ====================
PROJECT_NAME=SemAlign API
VERSION=1.0.0
DEBUG=True
PORT=8000

# ==================== 安全配置 ====================
# JWT 密钥（生产环境必须使用强密钥）
SECRET_KEY=your-secret-key-here-change-in-production
# Token 过期时间（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ==================== 数据库配置 ====================
# SQLite 数据库（开发环境）
DATABASE_URL=sqlite:///./data/standards.db

# PostgreSQL 数据库（生产环境）
# DATABASE_URL=postgresql://user:password@localhost:5432/semalign

# ==================== CORS 配置 ====================
# 允许跨域的源地址（逗号分隔）
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 5. 初始化数据库

```bash
# 表结构会在应用启动时（main.py lifespan）自动 create_all
# 亦可手动执行：
python scripts/create_tables.py
# 或：
python -c "from core.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### 6. 创建管理员用户

```bash
# 推荐：使用项目脚本（默认 admin / admin123，已存在则跳过）
python scripts/init_user.py
```

重置密码可使用 `python scripts/update_password.py`（按脚本内提示操作）。

### 7. 启动应用

#### 开发环境（支持热重载）

```bash
# 方式 1：使用 main.py（推荐）
python main.py

# 方式 2：使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 生产环境

```bash
# 使用 gunicorn + uvicorn workers
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### 8. 验证服务

访问以下地址验证服务是否正常运行：

* **根路径**: <http://localhost:8000>

* **健康检查**: <http://localhost:8000/health>

* **Swagger UI（交互式接口文档）**: <http://localhost:8000/docs> — 若误输成 `/doc`（少一个 s），服务会 **307 重定向到 `/docs`**。需在 Swagger 中点击 **Authorize** 填入 `Bearer <access_token>` 才能试受保护路由。在 `main.py` 里 `docs_url` 可改为 `None` 关闭文档页（常见于上线）。

* **OpenAPI 规范（原始 JSON）**: <http://localhost:8000/openapi.json>（与 Swagger / ReDoc 同源数据，可导入 Postman / Swagger Editor 等）

* **ReDoc**: <http://localhost:8000/redoc>。在 `main.py` 里 `redoc_url` 可改为 `None` 关闭。

### 9. 测试接口

#### 登录获取 Token

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

#### 使用 Token 访问受保护接口

```bash
# 将 YOUR_ACCESS_TOKEN 换为登录返回 JSON 中 data.access_token
curl -X GET "http://localhost:8000/api/standards" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 10. 常见问题

**问题 1：启动时提示 "SECRET_KEY must be set"**

* 解决：确保 .env 文件中配置了 SECRET_KEY

**问题 2：数据库连接失败**

* 解决：检查 DATABASE_URL 配置是否正确

**问题 3：跨域问题**

* 解决：检查 CORS_ORIGINS 是否包含前端地址

**问题 4：端口被占用**

* 解决：修改 .env 中的 PORT 或在启动命令中指定其他端口

**问题 5：**`pip install`**&#x20;报 externally-managed-environment 或 numpy / opencv 版本冲突**

* 解决：务必先创建并**激活**本节「### 2. Python 虚拟环境」中的 `.venv`，再在虚拟环境内执行 `pip install -r requirements.txt`；勿向系统 Python 全局安装。

## 🔐 认证流程

1. 登录获取 Token：`POST /api/auth/login`，请求体为 `{ "username", "password" }`。\
   成功时为统一响应 `{ "code", "message", "data" }`，JWT 在 `data.access_token`（另有 `token_type`、`user`）。

2. 在请求头中使用 Token：

```text
Authorization: Bearer <access_token>
```

## 📚 API 模块

所有业务接口均在 `/api` 下；完整列表以运行实例的 `/openapi.json` 或本仓库 `routers/` 为准。

| 模块    | 前缀                | 主要端点                                                                 |
| ----- | ----------------- | -------------------------------------------------------------------- |
| 认证    | `/api/auth`       | `POST /login`，`GET /me`                                              |
| 用户资料  | `/api/user`       | `GET /profile`，`PUT /profile`                                        |
| 工作台   | `/api/workbench`  | `GET /dashboard`                                                     |
| 标准管理  | `/api/standards`  | 列表/详情/增删改（`GET ""`、`GET /{id}`、`POST ""`、`PUT /{id}`、`DELETE /{id}`） |
| 标准库统计 | `/api`            | `GET /statistics`                                                    |
| 标准导入  | `/api/import`     | `POST /`（批量 Standard JSON）、`POST /upload`、`POST /records`            |
| 智能检索  | `/api/search`     | `GET /`、`GET /suggest`                                               |
| 标准对齐  | `/api/alignment`  | `POST/GET /tasks`、`GET/DELETE /tasks/{id}`、`POST /tasks/{id}/save`   |
| 比对结果  | `/api/comparison` | `GET /task                                                           |
| 导出报告  | `/api/export`     | `GET /report/{task_id}`（Excel）                                       |
| 规则引擎  | `/api/rules`      | `POST /evaluate`，`GET /list`，`GET /config/default`                   |
| 系统    | `/`               | `GET /`，`GET /health`                                                |

**认证**：除登录与健康检查外，多数接口需在请求头携带 `Authorization: Bearer <token>`。

## 🛠️ 开发规范

### 代码风格

* 使用 Black 进行代码格式化

* 使用 isort 进行导入排序

* 使用 flake8 进行代码检查

### 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 测试

```bash
# 运行测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=semAlign_backend --cov-report=html
```

⠀