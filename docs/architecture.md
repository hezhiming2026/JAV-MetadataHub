# JAV-MetadataHub 架构

本文档描述当前实现状态和后续边界。它不定义新的服务层、查询层、导出器或实体解析算法。

## 项目定位

JAV-MetadataHub 是一个公开元数据底座，目标是把外部结构化来源转换为可审计、可查询、可分析的内部数据。

核心数据路径：

```text
external metadata source
    -> source_records
    -> parser
    -> field_observations
    -> canonical tables
    -> read-only API
```

当前实现已经覆盖 source evidence、observations、FANZA/R18 的基础 ingestion flow、FANZA
works-only canonical promotion MVP 和只读 API。dimensions/relationships promotion、entity
resolution、Gold exports 和 CSV/Parquet exporter 仍是后续计划。

## 数据分层

| Layer | 当前状态 | 主要对象 |
| --- | --- | --- |
| Bronze | 已实现 | `collector_runs`, `source_records` |
| Silver observations | 已实现 | `field_observations` |
| Silver canonical tables | schema 和只读 repository/API 已实现；FANZA works-only promotion MVP 已实现；dimensions 和 relationships 自动提升规则未实现 | `works`, `people`, `companies`, `series`, `tags`, relationship tables |
| Gold | 未实现 | future views / CSV / Parquet / DuckDB exports |

## Source Records

`source_records` 是所有外部记录的第一落点。当前 repository 支持：

- create
- get by ID
- get by `(source, source_key, record_type)`
- PostgreSQL upsert
- read-only pagination for API

collector、importer 或 runner 不负责最终 transaction 边界；调用方决定 commit 或 rollback。

## Field Observations

`field_observations` 保存来源对字段值的声明。当前允许状态：

- `active`
- `rejected`
- `superseded`

`accepted` 不是 observation status。后续 canonical promotion 如需表达字段被采纳，应通过明确的 promotion / audit 机制实现，而不是修改 observation status 语义。

当前 service 支持：

- 记录 observation。
- 对 active observations 做 best-effort 幂等。
- 只读分页查询。

## R18.dev 当前链路

当前 R18 实现只支持本地 structured JSON / JSONL records：

```text
local JSON/JSONL rows
    -> R18DumpImporter
    -> SourceRecordRepository.upsert
    -> R18DumpParser
    -> FieldObservationService.record_observation
```

当前不支持真实 R18 `.sql` / `.sql.gz` dump。真实 SQL dump 的 staging / restore / extraction 需要后续单独实现。

## FANZA / DMM 当前链路

当前 FANZA 实现包含：

- async API client
- collector
- collector run repository
- parser
- single source record observation ingestion
- batch ingestion
- CLI runner

当前 observation 链路：

```text
FanzaClient
    -> FanzaCollector
    -> source_records
    -> FanzaParser
    -> FieldObservationService
    -> field_observations
```

FANZA observations 显式使用较高 confidence。当前已支持 works-only canonical promotion MVP，
但不创建 people、companies、series、tags 或 relationship rows。

## FastAPI Read-only API

当前 API 使用 factory 入口：

```bash
.venv/bin/uvicorn jav_metadatahub.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

已实现 endpoints：

- `GET /health`
- `GET /works`, `GET /works/{id}`
- `GET /people`, `GET /people/{id}`
- `GET /companies`, `GET /companies/{id}`
- `GET /series`, `GET /series/{id}`
- `GET /tags`, `GET /tags/{id}`
- `GET /observations`
- `GET /source-records`, `GET /source-records/{id}`

API routes 保持薄层：

- 参数校验。
- 构造具体 repository 或已有 service。
- 调用只读方法。
- 404 处理。
- Pydantic response serialization。

所有 list endpoints 使用：

```json
{"data": [], "limit": 20, "offset": 0, "total": 0}
```

默认测试不连接真实 PostgreSQL；真实 PostgreSQL smoke test 已作为人工验证通过。

## 当前未实现能力

以下能力是 backlog，不属于当前已实现系统：

- dimensions / relationships canonical promotion rules。
- entity resolution / merge workflow。
- CSV / Parquet exporter。
- Gold datasets / materialized views / DuckDB exports。
- API write endpoints。
- JavDB / JavBus / JavLibrary / AVWikiDB supplement ingestion。
- 真实 R18 `.sql` / `.sql.gz` dump restore and extraction。

## 测试策略

默认验证命令：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

测试原则：

- 外部 API 使用 mocked HTTP。
- 默认 pytest 不依赖真实 PostgreSQL。
- parser 不 import repositories 或 services。
- API route tests 使用 dependency override 或 mocked session。
- 真实 PostgreSQL 验证作为人工 smoke test，不作为默认测试依赖。
