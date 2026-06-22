# JAV-MetadataHub

JAV-MetadataHub 是一个面向日本成人成人视频元数据分析的公开元数据底座。

项目采集、标准化、治理并导出作品、公开演职员名称、公司、系列、标签、external IDs、source records 和 field observations 等元数据。它的核心目标是为下游数据分析、只读 API、CSV / Parquet / DuckDB 导出提供可追溯的数据基础。

## 范围

V1 聚焦公开元数据建模、source records、field observations、canonical entities、导出和只读 API。

处理的数据包括：

* 作品元数据：番号、标题、发行日期、时长、类型、external IDs、external URLs。
* 公开人物元数据：女优、男优、导演、公开艺名、别名、source IDs。
* 公司元数据：maker、label、publisher、studio。
* 系列元数据。
* 标签元数据：genre、keyword、theme。
* 来源追溯信息：source、source key、source URL、confidence、fetched/imported time。
* 来源证据：raw JSON、由 SQL dump 派生的 row、后续来源样本。

媒体字段在 V1 作为 URL metadata 保存。版权、访问策略、地域可用性等问题在来源规格和产品发布阶段单独评估。

## 架构

```text
external metadata sources
    ↓
collectors / importers
    ↓
source_records
    ↓
parsers
    ↓
field_observations
    ↓
silver canonical entities
    ↓
gold analytics exports
    ↓
CSV / Parquet / DuckDB / REST API
```

## 数据源策略

V1 使用稳定结构化来源：

1. R18.dev dump：作为 seed、historical dataset 和 backfill 来源。
2. FANZA / DMM API：作为官方结构化 metadata 来源。

后续版本可以增加补充观察来源：

* Javinizer-Go
* MetaTube
* JavDB
* JavBus
* JavLibrary
* AVWikiDB

补充来源用于缺失字段、冲突提示或人工校对线索。外部来源数据先进入 `source_records`，再由 parser 转换为 `field_observations`；canonical 字段通过明确的解析和提升逻辑更新。

默认字段提升优先级：

```text
FANZA/DMM API > R18.dev dump > supplemental observations > unknown
```

## 核心表

* `collector_runs`
* `source_records`
* `field_observations`
* `works`
* `work_external_ids`
* `people`
* `person_aliases`
* `person_external_ids`
* `work_people`
* `companies`
* `company_external_ids`
* `work_companies`
* `series`
* `series_external_ids`
* `work_series`
* `tags`
* `work_tags`
* `entity_match_candidates`
* `entity_merge_logs`
* `media_assets`

## 技术栈

* Python 3.12+
* PostgreSQL 15+
* SQLAlchemy 2.x
* Alembic
* Pydantic v2
* pydantic-settings
* httpx
* tenacity
* FastAPI
* Typer
* pytest
* ruff
* mypy
* DuckDB / Parquet

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

编辑 `.env`。

### 4. 启动 PostgreSQL

```bash
docker compose up -d postgres
```

### 5. 运行 migrations

```bash
alembic upgrade head
```

### 6. 运行测试

```bash
pytest
```

### 7. 启动 API

```bash
uvicorn jav_metadatahub.api.main:app --reload
```

## 开发命令

```bash
ruff check .
ruff format .
mypy src
pytest
```

## 文档

* `docs/architecture.md`
* `docs/schema.md`
* `docs/data_sources.md`
* `docs/codex_tasks.md`
* `docs/source_specs/r18_dump.md`
* `docs/source_specs/fanza_dmm_api.md`
* `docs/source_specs/javdb.md`
* `docs/source_specs/javbus.md`
* `docs/source_specs/javlibrary.md`
* `docs/source_specs/avwikidb.md`

## 数据治理原则

* 原始来源证据在标准化前保存到 `source_records`。
* 不确定、冲突或来源特定字段保存到 `field_observations`。
* canonical 字段代表当前最佳值；更新 canonical 前保留对应 observation。
* 每个提升后的 canonical 值应能回溯到 source record 和 field observation。
