# Codex 任务拆解

本文档记录当前真实任务历史和后续 backlog。任务边界以 `source_records -> field_observations -> canonical`
的数据治理路径为准。

## 已完成任务

### Task 1：初始化项目结构

创建 Python 3.12 项目骨架、`pyproject.toml`、基础包结构、配置、CLI 入口、Alembic 基础文件和测试框架。

验收状态：

- package import 通过。
- CLI import 通过。
- 基础 pytest / ruff / mypy 验证可运行。

### Task 2：数据库模型和 Alembic migration

实现 PostgreSQL `javhub` schema、SQLAlchemy 2.x typed models、session helper 和初始 Alembic migration。

验收状态：

- metadata tests 覆盖核心表、约束和关键设计。
- 初始 migration 已在真实 NAS PostgreSQL 上验证通过。
- `alembic current` 曾验证为 `0001_initial_schema (head)`。

### Task 3：番号标准化模块

实现 `normalize_code()` 和 `NormalizedCode`，用于生成 code original / norm / prefix / number。

验收状态：

- 覆盖大小写、分隔符、前导零、混合 prefix、空输入和极端分隔符输入。

### Task 4：`source_records` repository

实现 raw source evidence 的 create / get / upsert，并支持保存 JSON object、JSON array、HTML、text、失败状态和 fetch metadata。

验收状态：

- PostgreSQL `ON CONFLICT` upsert 以 `(source, source_key, record_type)` 为冲突目标。
- repository 不负责 commit。
- 后续 Task 12 已补充 read-only pagination。

### Task 5：`field_observations` repository / service

实现字段观察记录的 create、查询、状态更新、字段值文本生成和 active duplicate best-effort 幂等。

验收状态：

- `observation_status` 只允许 `active / rejected / superseded`。
- `field_value` 使用 JSONB bind，避免 PostgreSQL `jsonb = varchar` 错误。
- service 不修改 canonical tables。

### Task 6：R18.dev 本地 structured dump importer

实现 R18 本地 structured JSON / JSONL records importer 和 parser。

当前边界：

- 支持 `.json` 和 `.jsonl`。
- 不支持真实 `.sql` / `.sql.gz` dump。
- 不访问网络。
- 写入 `source_records` 和 staging observations。

### Task 7：FANZA / DMM API client

实现 async `FanzaClient`，负责请求构造、认证参数注入、限速、重试、错误处理、JSON 返回和 secret redaction。

当前边界：

- 测试使用 mocked HTTP。
- 不落库。
- 不解析字段。

### Task 8：FANZA collector

实现 `FanzaCollector` 和 `CollectorRunRepository`，调用 `FanzaClient` 获取 raw JSON，并写入 `source_records`。

当前边界：

- 不解析字段。
- 不写 observations。
- 不创建 canonical rows。
- 不统计 client 内部 retry attempts。

### Task 9：FANZA parser + observation ingestion

实现纯解析层 `FanzaParser` 和 `FanzaObservationIngestionService`，从 FANZA work source record 解析字段并写入
`field_observations`。

当前边界：

- parser 不 import repositories 或 services。
- ingestion 使用 `entity_type="fanza_work"` 和 `source_record.id` 作为 staging entity。
- 不做 canonical promotion。

### Task 10：FANZA source_records -> observations batch ingestion

实现 FANZA observations 批量编排，从 `source_records` 分页读取 `source="fanza"`、`record_type="work"` 的记录，
并调用单条 ingestion service。

当前边界：

- 支持 `limit`、`offset`、`dry_run`、`idempotent`、`continue_on_error`。
- batch service 不负责 commit。
- 不调用真实 FANZA API。

### Task 11：FANZA observation ingestion runner / CLI

实现受控 runner / CLI，用于执行 FANZA source records 到 observations 的批量处理。

当前边界：

- 默认 rollback。
- 只有显式 `--commit` 且 `failed_count == 0` 时 commit。
- `--dry-run --commit` 是非法组合。
- runner 只构造 repository/service graph、调用 batch ingestion、管理事务。

### Task 12：FastAPI read-only API

实现只读 API：

- `GET /health`
- `GET /works`, `GET /works/{id}`
- `GET /people`, `GET /people/{id}`
- `GET /companies`, `GET /companies/{id}`
- `GET /series`, `GET /series/{id}`
- `GET /tags`, `GET /tags/{id}`
- `GET /observations`
- `GET /source-records`, `GET /source-records/{id}`

当前边界：

- route 是 thin controller。
- API 只读。
- list endpoints 支持 `limit / offset` 和统一分页响应。
- 已通过真实 PostgreSQL smoke test。

### Task 13：测试和文档收尾

目标：

- 同步 README、architecture、schema、data sources、source specs 和任务文档。
- 明确已实现能力与后续计划。
- 保持默认测试不依赖真实 PostgreSQL。
- 运行 pytest / ruff / format check / mypy。

## 后续 Backlog

### Backlog：canonical promotion

实现从 high-confidence observations 到 canonical fields 的显式提升规则。

要求：

- 保留 source record 和 observation provenance。
- 不盲目覆盖已有 canonical 值。
- 冲突值继续保留在 `field_observations`。

### Backlog：entity resolution

实现保守 entity matching 和 merge workflow。

要求：

- people 不得仅根据姓名自动合并。
- ambiguous matches 写入 `entity_match_candidates`。
- accepted merges 写入 `entity_merge_logs`。

### Backlog：CSV / Parquet exporter

实现 Silver tables 和未来 Gold datasets 的导出。

要求：

- 支持 CSV 和 Parquet。
- 空表 graceful behavior。
- 默认不影响 ingestion/API。

### Backlog：Gold datasets

实现面向分析的 denormalized views 或 exports。

候选对象：

- `gold_work_flat`
- `gold_person_profile`
- `gold_company_monthly_stats`
- `gold_tag_monthly_trends`

### Backlog：补充来源

后续评估 Javinizer-Go、MetaTube、JavDB、JavBus、JavLibrary 和 AVWikiDB。

要求：

- 先写 `source_records`。
- 再写 `field_observations`。
- 不直接覆盖 canonical。
- 默认不做全站 HTML 爬取。

## 通用验证命令

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```
