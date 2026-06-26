# JAV-MetadataHub

JAV-MetadataHub 是一个面向日本成人视频公开元数据分析的底座项目。它围绕
`source_records -> parser -> field_observations -> canonical -> read-only API`
建立可追溯的数据链路，用于后续分析、审计和只读查询。

## 当前已实现

- Python 3.12 项目骨架、配置、日志和 Typer CLI 入口。
- PostgreSQL `javhub` schema、SQLAlchemy 2.x typed models 和初始 Alembic migration。
- `source_records` repository，支持原始来源证据 create / get / upsert / pagination。
- `field_observations` repository 和 service，支持字段观察记录、幂等写入和只读分页查询。
- 番号标准化模块。
- R18.dev 本地 structured JSON / JSONL importer 和 parser。
- FANZA / DMM async API client、collector、parser、observation ingestion、batch ingestion 和 CLI runner。
- FANZA works-only canonical promotion MVP，可从 `fanza_work` observations 提升 `works` 与
  `work_external_ids`。
- FastAPI read-only API：
  - `GET /health`
  - `GET /works`, `GET /works/{id}`
  - `GET /people`, `GET /people/{id}`
  - `GET /companies`, `GET /companies/{id}`
  - `GET /series`, `GET /series/{id}`
  - `GET /tags`, `GET /tags/{id}`
  - `GET /observations`
  - `GET /source-records`, `GET /source-records/{id}`

## 后续计划

以下能力尚未实现，不应被视为当前已完成行为：

- people / companies / series / tags canonical promotion 规则。
- work_people / work_companies / work_series / work_tags relationship promotion。
- entity resolution 和 entity merge workflow。
- CSV / Parquet exporter。
- Gold datasets / materialized views / DuckDB exports。
- API 写操作。
- JavDB / JavBus / JavLibrary / AVWikiDB 补充来源接入。
- 真实 R18 `.sql` / `.sql.gz` dump importer。

## 数据治理原则

- 原始来源证据在标准化前保存到 `source_records`。
- 解析出的字段声明先保存到 `field_observations`。
- canonical 字段代表后续规则选择出的当前最佳值；当前自动提升规则尚未实现。
- 补充来源不得直接覆盖 canonical 字段。
- 每个被提升的 canonical 值应能回溯到 source record 和 field observation。
- V1 图片和媒体字段只保存 URL metadata。

## 数据源策略

V1 使用两个结构化来源：

1. R18.dev 本地 structured JSON / JSONL records。
2. FANZA / DMM API。

R18 当前实现不支持真实 `.sql` / `.sql.gz` dump。FANZA 当前实现支持 raw responses 写入
`source_records`，通过 parser / ingestion 写入 `field_observations`，并支持 works-only canonical
promotion；dimensions、relationships、entity resolution 和 exporter 尚未实现。

后续补充来源包括 Javinizer-Go、MetaTube、JavDB、JavBus、JavLibrary 和 AVWikiDB。它们应作为补充
observation 来源评估，而不是直接写 canonical。

## 技术栈

- Python 3.12+
- PostgreSQL 15+
- SQLAlchemy 2.x
- Alembic
- Pydantic v2 / pydantic-settings
- httpx / tenacity
- FastAPI / Typer
- pytest / ruff / mypy
- DuckDB / Parquet 依赖已保留，exporter 尚未实现

## 快速开始

### 1. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -e ".[dev]"
```

### 3. 配置环境

```bash
cp .env.example .env
```

编辑 `.env`，至少配置 `DATABASE_URL`。不要提交 `.env`。

### 4. 运行 migrations

```bash
.venv/bin/alembic upgrade head
```

### 5. 运行测试和检查

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
```

## 启动只读 API

使用已验证的 factory 方式启动：

```bash
.venv/bin/uvicorn jav_metadatahub.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

基础 smoke test：

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/source-records?limit=5"
curl "http://127.0.0.1:8000/observations?limit=5"
curl "http://127.0.0.1:8000/works?limit=5"
curl "http://127.0.0.1:8000/people?limit=5"
curl "http://127.0.0.1:8000/companies?limit=5"
curl "http://127.0.0.1:8000/series?limit=5"
curl "http://127.0.0.1:8000/tags?limit=5"
```

所有 list endpoints 返回统一分页结构：

```json
{"data": [], "limit": 5, "offset": 0, "total": 0}
```

真实 PostgreSQL smoke test 已验证：空 canonical 表不会 500，会返回空分页结构。

## 文档

- `docs/architecture.md`
- `docs/schema.md`
- `docs/data_sources.md`
- `docs/codex_tasks.md`
- `docs/source_specs/r18_dump.md`
- `docs/source_specs/fanza_dmm_api.md`
- `docs/source_specs/javdb.md`
- `docs/source_specs/javbus.md`
- `docs/source_specs/javlibrary.md`
- `docs/source_specs/avwikidb.md`
