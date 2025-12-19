# CPS Growth Copilot v1.0 - 淘客侧

CPS Growth Copilot 是一个基于真实公开数据的智能推荐系统，专为淘客侧设计。本项目严格使用真实数据，不包含任何虚构业务数据，也不使用爬虫。

## 核心特性

- ✅ **真实数据**: 使用 HuggingFace Amazon Reviews 2023 真实数据集
- ✅ **可解释推荐**: 每个推荐都有明确的理由（reasons）
- ✅ **配置化护栏**: 通过 YAML 配置灵活控制推荐质量
- ✅ **轻量级数据库**: 使用 DuckDB，无需独立数据库服务
- ✅ **完整测试**: 包含护栏系统的单元测试

## 快速开始

### 前置要求

- Python 3.10+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 完整验证流程（4 步）

#### 1. 导入 All_Beauty 数据（小规模）

```bash
python -m scripts.bootstrap_data --category All_Beauty --meta-limit 200 --reviews-limit 2000 --scan-limit 10000 --reset
```

**预期输出**:
```
📦 Importing 1 category/categories: All_Beauty
Using HuggingFace cache: data/hf_cache
✅ Found meta file: raw/meta_categories/meta_All_Beauty.jsonl
✅ Found review file: raw/review_categories/All_Beauty.jsonl
Import meta: 100%|████████| 200/200
Scan reviews: 100%|████████| 2000/2000

=== Import Summary ===
Total Items: 200
Total Reviews: 33
```

#### 2. 验证数据库

```bash
python -m scripts.inspect_db
```

**预期输出**:
```
==================================================
Database Statistics
==================================================
DB (relative): data/duckdb/cps_growth.duckdb
DB (absolute): D:\Download\cursor\cps-growth-copilot\data\duckdb\cps_growth.duckdb

Tables in database:
  - items
  - reviews

Items: 200
Reviews: 33
Item Stats: 0

✅ Database contains data: 200 items, 33 reviews
```

#### 3. 启动 API 服务

```bash
uvicorn app.api.main:app --reload --port 8081
```

**预期输出**:
```
INFO:     Uvicorn running on http://127.0.0.1:8081
INFO:     Application startup complete.
```

#### 4. 测试 API

```bash
# 推荐 API - 关键词搜索
curl "http://127.0.0.1:8081/api/recommend?q=serum&top_n=5"

# 推荐 API - 全局 Top-N
curl "http://127.0.0.1:8081/api/recommend?top_n=5"

# 漏斗诊断 API（需要先导入天池数据）
curl "http://127.0.0.1:8081/api/funnel/diagnose?item_id=123456&lookback_days=7"
```

**推荐 API 预期输出**:
```json
{
  "query": "serum",
  "category": null,
  "candidates": 10,
  "passed": 5,
  "filtered_stats": {
    "min_avg_rating": 3.5,
    "min_rating_count": 10,
    "price_min": 0.0,
    "price_max": 1000.0
  },
  "items": [
    {
      "parent_asin": "B001...",
      "title": "...",
      "price": 19.99,
      "score": 0.8234,
      "reasons": [
        "评分高（4.5分）",
        "评论多（150条）",
        "价格带匹配（$19.99）"
      ],
      "risk_flags": [],
      "commission_rate": 0.12,
      "estimated_commission": 2.40,
      "commission_note": "simulated"
    }
  ]
}
```

### 导入数据

#### Linux/Mac (Bash)

```bash
# 单类目导入（小规模，用于快速验证）
python -m scripts.bootstrap_data --category All_Beauty --meta-limit 200 --reviews-limit 2000 --scan-limit 10000

# 导入 3C 类目（自动映射为 Electronics）
python -m scripts.bootstrap_data --category 3C --meta-limit 200 --reviews-limit 2000 --scan-limit 10000

# 多类目导入（逗号分隔）
python -m scripts.bootstrap_data --categories All_Beauty,Electronics --meta-limit 200 --reviews-limit 2000 --scan-limit 10000

# 中等规模导入
python -m scripts.bootstrap_data --category All_Beauty --meta-limit 20000 --reviews-limit 60000 --scan-limit 300000
```

#### Windows (PowerShell)

**重要提示**: 在 PowerShell 中，不要直接输入 Python 语句。使用以下方式：

```powershell
# 方式 1: 使用 python -m（推荐）
python -m scripts.bootstrap_data --category All_Beauty --meta-limit 200 --reviews-limit 2000 --scan-limit 10000

# 方式 2: 使用 python -c（单行命令）
python -c "import sys; sys.path.insert(0, '.'); from scripts.bootstrap_data import main; main()" --category All_Beauty --meta-limit 200 --reviews-limit 2000

# 方式 3: 进入 Python REPL（交互式）
python
>>> import sys
>>> sys.path.insert(0, '.')
>>> from scripts.bootstrap_data import main
>>> import sys
>>> sys.argv = ['bootstrap_data.py', '--category', 'All_Beauty', '--meta-limit', '200', '--reviews-limit', '2000']
>>> main()
```

**为什么？** PowerShell 的语法解析可能与 Python 参数冲突，使用 `python -m` 是最安全的方式。

参数说明：
- `--category`: 单个类别名称（如 All_Beauty, 3C, Electronics）
  - `3C` 会自动映射为 `Electronics`
- `--categories`: 多个类别（逗号分隔，如 `All_Beauty,Electronics`）
- `--meta-limit`: 每个类别的商品元数据数量限制（默认 5000）
- `--reviews-limit`: 每个类别的评价数据数量限制（默认 20000）
- `--scan-limit`: 每个类别扫描数据集的数量限制（默认 120000）
- `--hf-cache-dir`: HuggingFace 缓存目录（默认 data/hf_cache）
- `--reset`: 清空表后重新导入

**类别映射**:
- `3C` / `3c` / `electronics` → `Electronics`
- 其他类别名称保持原样

**多类目导入**: 使用 `--categories` 可以一次导入多个类别，数据会存储在同一个数据库中，通过 `category` 列区分。

### 检查数据

```bash
# Linux/Mac
python -m scripts.inspect_db

# Windows PowerShell
python -m scripts.inspect_db
```

### 启动 API 服务

```bash
# 默认端口 8081
uvicorn app.api.main:app --reload --port 8081
```

API 将在 http://127.0.0.1:8081 运行。

### 测试 API

#### 推荐 API

```bash
# 健康检查
curl http://127.0.0.1:8081/health

# 获取推荐（关键词搜索）
curl "http://127.0.0.1:8081/api/recommend?q=serum&top_n=10"

# 获取推荐（全局 Top-N）
curl "http://127.0.0.1:8081/api/recommend?top_n=10"

# 按类别过滤
curl "http://127.0.0.1:8081/api/recommend?category=All_Beauty&top_n=10"

# 带价格过滤
curl "http://127.0.0.1:8081/api/recommend?q=serum&top_n=10&min_price=10&max_price=50"
```

#### 漏斗诊断 API（需要先导入天池数据）

```bash
# 诊断商品漏斗指标
curl "http://127.0.0.1:8081/api/funnel/diagnose?item_id=123456&lookback_days=7"
```

### 导入天池数据（可选）

```bash
# 导入天池 UserBehavior 数据
python -m scripts.import_tianchi_userbehavior --csv-path data/raw/tianchi/UserBehavior.csv --limit 10000
```

**注意**: 天池数据是独立的数据源，不与 Amazon 商品数据做 join，仅用于漏斗分析。

## 项目结构

```
cps-growth-copilot/
├── app/
│   ├── api/              # FastAPI 路由
│   │   ├── main.py
│   │   └── routers/
│   │       ├── recommend.py
│   │       └── funnel.py
│   ├── core/             # 核心配置和护栏
│   │   ├── settings.py
│   │   └── guardrails.py
│   ├── services/         # 推荐引擎和理由生成
│   │   ├── recommender.py
│   │   ├── reasons.py
│   │   ├── commission.py
│   │   └── funnel.py
│   └── storage/          # DuckDB 存储层
│       └── db.py
├── configs/              # YAML 配置文件
│   ├── guardrails.yaml
│   ├── scoring.yaml
│   ├── commission.yaml
│   └── funnel_rules.yaml
├── docs/                 # 文档
│   ├── README.md
│   ├── PRD.md
│   ├── SCHEMA.md
│   └── EVAL_RUBRIC.md
├── scripts/              # 工具脚本
│   ├── bootstrap_data.py
│   ├── inspect_db.py
│   ├── import_tianchi_userbehavior.py
│   └── build_funnel_features.py
├── tests/                # 测试
│   └── test_guardrails.py
├── data/                 # 数据目录
│   ├── duckdb/           # DuckDB 数据库文件
│   └── raw/              # 原始数据文件
├── requirements.txt
└── README.md
```

## API 端点

### 推荐接口

- `GET /api/recommend`
  - `q`: 可选关键词（搜索商品标题）
  - `top_n`: 返回推荐数量（1-100，默认 10）
  - `category`: 可选类别过滤（如 "All_Beauty", "Electronics"）
  - `min_price`: 可选最低价格过滤
  - `max_price`: 可选最高价格过滤
  
  返回字段：
  - `score`: 推荐分数
  - `reasons`: 2-3 条可解释原因
  - `risk_flags`: 护栏违规列表（如有）
  - `commission_rate`: 模拟佣金率
  - `estimated_commission`: 模拟佣金金额
  - `commission_note`: "simulated"（明确标注为模拟值）

### 漏斗诊断接口

- `GET /api/funnel/diagnose`
  - `item_id`: 商品 ID（必需）
  - `lookback_days`: 回溯天数（1-90，默认 7）
  
  返回字段：
  - `metrics`: 漏斗指标（pv, cart, fav, buy, 转化率）
  - `drop_offs`: 流失环节识别
  - `recommendations`: 优化建议
  - `conclusion`: 诊断结论

### 健康检查

- `GET /health`

### API 文档

访问 http://127.0.0.1:8081/docs 查看交互式 API 文档。

## 技术栈

- **Python**: 3.10+
- **FastAPI**: Web API 框架
- **DuckDB**: 轻量级分析数据库
- **HuggingFace datasets**: 数据加载
- **PyYAML**: 配置文件管理
- **pandas/numpy**: 数据处理

## 数据来源

### Amazon Reviews 2023
- **来源**: HuggingFace `McAuley-Lab/Amazon-Reviews-2023`
- **子集**: `raw_meta_All_Beauty` 和 `raw_review_All_Beauty`
- **用途**: 商品元数据和用户评价数据
- **特点**: 真实商品信息，真实用户评价

### Tianchi UserBehavior
- **来源**: 天池用户行为数据集
- **文件**: `data/raw/tianchi/UserBehavior.csv`
- **用途**: 用户行为漏斗分析（pv/cart/fav/buy）
- **特点**: 独立数据源，不与 Amazon 商品数据 join
- **导入**: `python -m scripts.import_tianchi_userbehavior --csv-path data/raw/tianchi/UserBehavior.csv`

## 配置说明

### 护栏配置 (`configs/guardrails.yaml`)

控制推荐过滤规则：
- 最低评分
- 最低评价数量
- 价格区间
- 品牌黑名单
- ASIN 黑名单

### 评分配置 (`configs/scoring.yaml`)

控制推荐评分计算：
- 评分权重
- 流行度权重
- 时效性权重

## 运行测试

```bash
# 运行护栏测试
pytest tests/test_guardrails.py -v
```

## 文档

详细文档请查看 `docs/` 目录：
- `docs/README.md` - 作品集说明
- `docs/PRD.md` - 产品需求文档
- `docs/SCHEMA.md` - 数据库 Schema
- `docs/EVAL_RUBRIC.md` - 评估标准

## 注意事项

- 本项目使用真实公开数据，不包含任何虚构业务数据
- 数据通过 HuggingFace datasets 加载，无需爬虫
- 推荐结果仅基于公开数据，不包含商业机密
- 首次运行需要从 HuggingFace 下载数据，可能需要一些时间

## 许可证

MIT

## 当前进度（2025-12）

### 已完成
- 商家经营 Copilot 页面（merchant.html）：商家视角 + 小B选品视角的展示骨架
- 后端 Dashboard 聚合接口：`GET /merchant/dashboard`
- 最小“动作 API”（Demo 先产出可执行资产，不直接对接真实系统）：
  - `GET /merchant/actions/segment_sql?segment=dormant`
  - `GET /merchant/actions/message_template?type=cart_drop`
  - `GET /merchant/actions/export_users?segment=warm&limit=20000`（CSV 下载）
- 选品漏斗特征表脚本修复：兼容 Tianchi `behavior_type=1/2/3/4`，按“去重用户口径”构建 item 漏斗，避免出现 >100% 转化

### 数据源
- 行为：阿里天池 Tianchi（UserBehavior）
- 选品补充：Amazon 开源数据（Beauty；本地 hf_cache）

### 运行方式（Windows / PowerShell）
```powershell
cd D:\Download\cursor\cps-growth-copilot
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8081 --reload
