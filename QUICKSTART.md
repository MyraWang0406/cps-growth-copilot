# 快速开始指南

## 项目结构

```
cps-growth-copilot/
├── app/
│   ├── backend/          # FastAPI 后端
│   ├── frontend/         # Next.js 前端
│   └── infra/            # Docker 配置
├── docs/                 # 完整文档
├── scripts/              # 工具脚本
└── README.md
```

## 一键运行（推荐）

### Linux/Mac
```bash
chmod +x scripts/run_demo.sh
./scripts/run_demo.sh
```

### Windows
```bash
scripts\run_demo.bat
```

## 手动运行步骤

### 1. 启动数据库
```bash
cd app/infra
docker-compose up -d postgres
cd ../..
```

等待 10 秒让数据库就绪。

### 2. 初始化数据库和导入数据
```bash
# Linux/Mac
./scripts/init_db.sh

# Windows (需要安装 psql 或使用 Docker exec)
docker exec -i cps_postgres psql -U cps_user -d cps_growth < app/infra/postgres/init.sql

# 导入示例数据
python scripts/load_sample_data.py
```

### 3. 启动后端
```bash
cd app/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

后端将在 http://localhost:8000 运行。

### 4. 启动前端（新终端）
```bash
cd app/frontend
npm install
npm run dev
```

前端将在 http://localhost:3000 运行。

## 验证运行

### 1. 检查后端
```bash
curl http://localhost:8000/health
# 应该返回: {"status":"ok","service":"cps-growth-copilot"}
```

### 2. 检查前端
打开浏览器访问 http://localhost:3000

### 3. 测试 API
```bash
# 获取淘客指标
curl http://localhost:8000/metrics/taoke/1?window=7d

# 获取诊断报告
curl http://localhost:8000/diagnosis/taoke/1?window=14d

# 获取机会
curl http://localhost:8000/opportunities/taoke/1?window=14d

# 运行告警
curl -X POST http://localhost:8000/alerts/run
```

## 常见问题

### 1. 数据库连接失败
- 确保 Docker 容器正在运行: `docker ps`
- 检查端口 5432 是否被占用
- 等待数据库完全启动（约 10 秒）

### 2. 前端无法连接后端
- 检查后端是否运行在 8000 端口
- 检查 `NEXT_PUBLIC_API_URL` 环境变量
- 检查 CORS 设置

### 3. 数据为空
- 确保运行了 `load_sample_data.py`
- 检查数据库中的数据: `docker exec -it cps_postgres psql -U cps_user -d cps_growth -c "SELECT COUNT(*) FROM orders;"`

### 4. Python 依赖安装失败
- 确保 Python 版本 >= 3.11
- 使用虚拟环境: `python -m venv venv`
- 升级 pip: `pip install --upgrade pip`

## 下一步

1. 查看 API 文档: http://localhost:8000/docs
2. 阅读完整文档: `docs/00_overview.md`
3. 探索前端功能: http://localhost:3000

## 停止服务

### Linux/Mac
```bash
# 停止后端和前端（Ctrl+C）
# 停止数据库
cd app/infra
docker-compose down
```

### Windows
```bash
# 关闭后端和前端窗口
# 停止数据库
cd app\infra
docker-compose down
```

