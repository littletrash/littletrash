# 📦 耗材管理系统

耗材全生命周期管理平台，覆盖入库、库存、领用、审批、出库、归还、报表全流程。

## 功能特性

| 模块 | 功能 |
|------|------|
| 🔐 认证 | JWT 登录 / 4 角色权限（管理员/教师/审批人/系统管理员） |
| 📊 工作台 | 实时统计卡片 + 消耗趋势图 + 类别占比图 + 库存预警 + 审批角标 |
| 📥 入库登记 | 采购入库 / 自动创建耗材 / 库存累加 / 字段校验 |
| 📋 库存查询 | 关键词搜索 / 类别筛选 / 高低预警着色 / 库存调整 |
| 📝 领用申请 | 可搜索耗材下拉 / 实时库存显示 / 我的申请记录 |
| ✅ 审批管理 | 待审批/待出库/已完成 三Tab / 自动审批(低于阈值) |
| 🔄 物品归还 | 完好/损坏/丢失 / 逾期罚款计算 / 库存恢复 / Excel 导出 |
| 🏭 供应商 | CRUD / 软删除 / 供货次数与金额统计 |
| 📈 报表导出 | 7 种 Excel 导出 / 数据预览 / 勾选选择性导出 / 多 Sheet 备份 |
| 👤 用户管理 | 新增/停用/启用/重置密码（系统管理员） |
| ⚙️ 系统配置 | 审批阈值 / 罚款率 / 借用天数 在线配置 |
| 📜 审计日志 | 全操作记录 / 不可删除 / 多维度筛选 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.0 |
| 认证 | JWT (python-jose) |
| 开发数据库 | SQLite |
| 生产数据库 | MySQL 8.0+ |
| 前端 | 原生 HTML/CSS/JS (SPA) |
| 图表 | Chart.js 4.4 |
| Excel | openpyxl |
| 部署 | Docker / docker-compose / Gunicorn + Uvicorn |

## 快速开始

### 开发环境

```bash
cd backend
pip install -r requirements.txt
python main.py
# 访问 http://localhost:8000
# API 文档 http://localhost:8000/docs
```

### 演示账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | 123456 | 耗材管理员（全部权限） |
| teacher01 | 123456 | 用户（查看+申请） |
| approver01 | 123456 | 审批人 |
| sysadmin | 123456 | 系统管理员 |

### 生产部署（Docker）

```bash
cp .env.example .env         # 编辑 SECRET_KEY
docker-compose up -d         # MySQL + App 一键启动
```

### 传统部署

```bash
# 1. 创建 MySQL 数据库
mysql -u root -p -e "CREATE DATABASE material_mgmt CHARSET utf8mb4;"
mysql -u root -p material_mgmt < database/schema.sql
mysql -u root -p material_mgmt < database/seed.sql

# 2. 配置环境变量
export DATABASE_URL="mysql+pymysql://root:密码@localhost:3306/material_mgmt"
export SECRET_KEY="$(openssl rand -hex 32)"

# 3. 启动
pip install -r backend/requirements.txt pymysql gunicorn
cd backend && gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 项目结构

```
managersys/
├── backend/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 配置常量
│   ├── database.py                # 数据库会话
│   ├── models.py                  # ORM 模型（8 张表）
│   ├── schemas.py                 # Pydantic Schema
│   ├── auth.py                    # JWT 认证 + 角色守卫
│   ├── excel_utils.py             # Excel 导出公共工具
│   ├── requirements.txt           # Python 依赖
│   └── routers/
│       ├── auth_router.py         # 认证 + 个人资料 + 头像
│       ├── material_router.py     # 耗材 CRUD + 库存调整
│       ├── inbound_router.py      # 入库管理
│       ├── requisition_router.py  # 领用申请
│       ├── approval_router.py     # 审批 + 出库
│       ├── return_router.py       # 归还 + 逾期罚款 + Excel
│       ├── supplier_router.py     # 供应商管理
│       ├── report_router.py       # 报表导出
│       ├── log_router.py          # 操作日志
│       ├── user_router.py         # 用户管理
│       └── config_router.py       # 系统配置
├── prototype/
│   └── index.html                 # 前端 SPA（单文件）
├── database/
│   ├── schema.sql                 # MySQL 建表脚本
│   ├── seed.sql                   # 示例数据
│   └── ER说明.md                   # 实体关系说明
├── 交接包/                         # 项目文档
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## API 概览

| 模块 | 端点前缀 | 接口数 |
|------|------|:--:|
| 认证 | `/api/auth` | 6 |
| 耗材 | `/api/materials` | 5 |
| 入库 | `/api/inbound-records` | 4 |
| 领用 | `/api/requisitions` | 6 |
| 审批 | `/api/approvals` | 4 |
| 归还 | `/api/returns` | 7 |
| 供应商 | `/api/suppliers` | 4 |
| 报表 | `/api/reports` | 8 |
| 日志 | `/api/audit-logs` | 2 |
| 用户 | `/api/users` | 4 |
| 配置 | `/api/config` | 2 |

## 业务状态机

```
draft ──→ pending ──→ approved ──→ signed(自动) ──→ returned_stock
            │            │                            ↑
            ├──→ rejected  └──→ (确认出库)              │
            └──→ returned ──→ pending                   │
                                                        │
                    归还 ←──────────────────────────────┘
```

## License

MIT © 2026 zachary
