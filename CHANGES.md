# 改动文件列表

## A. 统一 DB_PATH

### 修改的文件：
1. `app/core/settings.py` - 添加统一的 `DB_PATH` 常量
2. `app/storage/db.py` - 使用统一的 `DB_PATH`
3. `scripts/bootstrap_data.py` - 使用统一的 DB 路径
4. `scripts/inspect_db.py` - 使用统一的 DB 路径，改进错误提示

## B. 推荐 API

### 新增文件：
1. `app/services/commission.py` - 佣金计算服务
2. `configs/commission.yaml` - 佣金配置（模拟）

### 修改的文件：
1. `app/services/recommender.py` - 添加 category 过滤、commission 计算
2. `app/services/reasons.py` - 优化为返回 2-3 条原因
3. `app/api/routers/recommend.py` - 更新 API 参数和响应
4. `app/storage/db.py` - 支持 category 字段
5. `configs/guardrails.yaml` - 添加 category 黑名单

## C. 天池漏斗模块

### 新增文件：
1. `app/services/funnel.py` - 漏斗分析服务
2. `app/api/routers/funnel.py` - 漏斗诊断 API

### 修改的文件：
1. `scripts/import_tianchi_userbehavior.py` - 完整实现数据导入
2. `app/storage/db.py` - 添加 user_behavior 表 schema
3. `configs/funnel_rules.yaml` - 完善漏斗规则配置
4. `app/api/main.py` - 添加 funnel 路由

## D. 文档更新

### 修改的文件：
1. `README.md` - 添加完整验证流程和 API 调用示例


