# Codex 任务拆解

本文档是后续工程任务的执行入口，来源于 `README.md`、`AGENTS.md`、`docs/architecture.md`、`docs/schema.md` 和 `docs/data_sources.md`。

任务拆解强调小步交付、证据链入库、可测试 parser 和保守实体解析。所有外部来源数据先进入 `source_records`，字段级结论写入 `field_observations`，canonical 更新通过明确服务逻辑完成。

## Task 1：初始化项目结构

**任务目标：** 创建 Python 项目骨架，不实现业务逻辑。

**输入文件：**

- `README.md`
- `AGENTS.md`
- `docs/architecture.md`

**输出文件：**

- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `docker-compose.yml`
- `src/jav_metadatahub/__init__.py`
- `tests/`
- import check 需要的可选 package placeholder modules

**需求：**

- 使用 Python 3.12+。
- 配置项目 metadata、runtime dependencies 和 dev dependencies。
- 包含 SQLAlchemy、Alembic、Pydantic v2、pydantic-settings、httpx、tenacity、FastAPI、Typer、pytest、ruff、mypy、DuckDB 和 Parquet 相关依赖。
- 添加不含真实凭证的 `.env.example`。
- 让 `python -c "import jav_metadatahub"` 可以运行。
- 本任务只做骨架，不实现 collectors、parsers、importers、API routes 或 database models。

**验收标准：**

- `pip install -e ".[dev]"` 或选定的安装命令可以运行。
- `python -c "import jav_metadatahub"` 成功。
- `ruff check .`、`ruff format --check .` 和 `pytest` 可针对空骨架运行。

## Task 2：数据库模型和 Alembic Migration

**任务目标：** 将 `docs/schema.md` 中的 schema 实现为 SQLAlchemy 2.x typed models 和初始 Alembic migration。

**输入文件：**

- `docs/schema.md`
- `docs/architecture.md`

**输出文件：**

- `src/jav_metadatahub/db/base.py`
- `src/jav_metadatahub/db/session.py`
- `src/jav_metadatahub/db/models.py` 或拆分后的 model modules
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/<initial_revision>.py`
- model/import tests

**需求：**

- 创建 `javhub` schema。
- 实现 `docs/schema.md` 列出的核心表。
- 保留 primary keys、foreign keys、unique constraints、confidence fields、provenance fields 和 indexes。
- 使用 SQLAlchemy 2.x typed declarative models。
- 通过 pydantic-settings 读取 `DATABASE_URL`。
- 本任务不添加 source-specific collection/parsing 逻辑。

**验收标准：**

- Alembic 可在测试数据库中创建全部表。
- Model imports 通过。
- Schema tests 覆盖代表性 constraints 和 indexes。

## Task 3：番号标准化模块

**任务目标：** 实现确定性的 JAV code normalization。

**输入文件：**

- `docs/architecture.md`
- `docs/schema.md`

**输出文件：**

- `src/jav_metadatahub/normalizers/code.py`
- `tests/test_normalize_code.py`

**需求：**

- 实现 `normalize_code(code: str | None)`。
- 返回 original value、compact normalized value、prefix 和 numeric component。
- 覆盖 `ABP-477`、`abp477`、`ABP_477`、`ABP 477`、`ABP00477`、`h_123abc001` 等格式。
- 函数保持 deterministic 和 side-effect free。
- 本任务不查询外部来源。

**验收标准：**

- 参数化测试覆盖常见分隔符、大小写、zero padding、empty input 和复杂 prefix。
- Type checking 无明显错误。

## Task 4：`source_records` Repository

**任务目标：** 实现 raw source evidence 的 repository 操作。

**输入文件：**

- `docs/schema.md`

**输出文件：**

- `src/jav_metadatahub/repositories/source_records.py`
- repository tests

**需求：**

- 支持 create、get by ID、get by `(source, source_key, record_type)` 和 upsert。
- 保留 `raw_json`、`raw_html`、`raw_text`、`http_status`、`fetch_status`、`error_message`、`parser_version`、`checksum` 和 `collector_run_id`。
- 支持保存 failed 和 not-found records。
- Repository 只负责持久化，不解析 source payloads。

**验收标准：**

- 重复 upsert 更新同一 `(source, source_key, record_type)` row。
- Failed records 可以保存和读取。
- 测试使用本地 fixtures。

## Task 5：`field_observations` Service

**任务目标：** 实现字段级 observation 创建和查询 helper。

**输入文件：**

- `docs/schema.md`

**输出文件：**

- `src/jav_metadatahub/services/observations.py`
- observation tests

**需求：**

- 为 entity type、entity ID、field name、field value、source、source record ID、confidence 和 observed time 创建 observations。
- 支持按 entity、field 和 source 查询 observations。
- `field_value` 保存 JSON-compatible structured data，`field_value_text` 用于搜索和调试。
- 支持 active、rejected、superseded 等 observation statuses。
- Service 不直接改写 canonical 字段；canonical 提升由 ingestion/resolution 逻辑负责。

**验收标准：**

- 测试验证 observation creation、retrieval 和 status handling。
- 同一 entity field 可以共存冲突 observations。

## Task 6：R18.dev Dump Importer

**任务目标：** 将 R18.dev dump 数据导入 `source_records` 和 observations，并用 fixtures 覆盖测试。

**输入文件：**

- `docs/source_specs/r18_dump.md`
- `docs/schema.md`
- `docs/data_sources.md`

**输出文件：**

- `src/jav_metadatahub/importers/r18_dump_importer.py`
- `src/jav_metadatahub/parsers/r18_parser.py`
- R18 fixtures and tests

**需求：**

- 将 R18.dev 视为 structured dump source。
- 保留 dump version、import time、source key 和 source record ID。
- 导入记录先写入 `source_records`，再进入 normalization。
- 按 source spec 映射 works、people、companies、series、tags、image URLs 和 external IDs。
- 不确定或冲突值写入 `field_observations`。
- 本任务使用 dump/serialized fixture，不依赖 live source。

**验收标准：**

- Fixture import 创建 source records。
- Parsed fields 通过 ingestion logic 创建 observations 和 canonical candidates。
- 同一 source key 和 record type 重导保持幂等。

## Task 7：FANZA/DMM API Client

**任务目标：** 实现 FANZA/DMM API metadata calls 的 async client。

**输入文件：**

- `docs/source_specs/fanza_dmm_api.md`
- `docs/data_sources.md`

**输出文件：**

- `src/jav_metadatahub/collectors/fanza_client.py`
- client tests using mocked HTTP

**需求：**

- 使用 `httpx.AsyncClient`。
- 从 settings 读取 base URL、API ID 和 affiliate ID。
- 实现 FloorList、ItemList、ActressSearch、MakerSearch、GenreSearch 和 SeriesSearch。
- 附加所需 auth/query parameters。
- 使用 tenacity retries、conservative rate limiting 和 structured logging。
- 日志中对 secret-like values 做 redaction。
- 测试使用 mocked HTTP。

**验收标准：**

- Mocked tests 验证 request paths、parameters、pagination values、retry behavior 和 secret redaction。

## Task 8：FANZA Collector

**任务目标：** 采集 FANZA/DMM API responses，并将 raw payloads 保存到 `source_records`。

**输入文件：**

- `docs/source_specs/fanza_dmm_api.md`
- `docs/schema.md`

**输出文件：**

- `src/jav_metadatahub/collectors/fanza_collector.py`
- collector tests

**需求：**

- 使用 `FanzaClient`。
- 支持 date-window collection 和 pagination。
- 创建并更新 `collector_runs`。
- 每个 raw page 或 detail payload 在解析前保存。
- 支持 dry-run 和 max-pages controls 以便测试。
- 解析和 canonical 写入由后续 parser/ingestion service 负责。

**验收标准：**

- Mocked multi-page collection 存储预期 `source_records`。
- Collector run status 和 counters 被更新。
- Dry-run 不产生 database writes。

## Task 9：Parser + Ingestion Service

**任务目标：** 将 source records 解析为内部 DTOs，创建 observations，并通过明确规则更新 canonical entities。

**输入文件：**

- `docs/schema.md`
- `docs/source_specs/r18_dump.md`
- `docs/source_specs/fanza_dmm_api.md`

**输出文件：**

- `src/jav_metadatahub/parsers/base.py`
- `src/jav_metadatahub/parsers/fanza_parser.py`
- `src/jav_metadatahub/parsers/r18_parser.py`
- `src/jav_metadatahub/services/ingestion.py`
- parser and ingestion tests

**需求：**

- 解析 works、external IDs、people、companies、series、tags 和 media URLs。
- 将所有 source claims 保存为 observations。
- 通过 repositories/services 创建或复用 canonical entities。
- 保留 source record ID 和 confidence。
- media assets 在 V1 保存 URL metadata。
- 避免盲目覆盖 canonical 字段；people merge 依赖明确 identity evidence。

**验收标准：**

- Fixture source records 产生预期 entities、relationships 和 observations。
- 重复 ingestion 对 relationships 和 external IDs 保持幂等。
- Conflicts 保留在 observations。

## Task 10：实体解析

**任务目标：** 实现保守的 V1 entity resolution rules。

**输入文件：**

- `docs/schema.md`
- `docs/architecture.md`

**输出文件：**

- `src/jav_metadatahub/services/entity_resolution.py`
- entity resolution tests

**需求：**

- works 可按 same source external ID、FANZA/DMM content ID 或 `code_norm + maker + release_date` 匹配。
- people 自动匹配只使用 same source person external ID。
- companies/series/tags 只在 compatible source/type context 下匹配。
- 为 ambiguous matches 创建 `entity_match_candidates`。
- accepted merges 记录到 `entity_merge_logs`。

**验收标准：**

- Tests prove safe auto-match cases。
- Tests prove ambiguous cases create candidates。
- Tests prove same-name people are routed to candidates rather than auto-merged。

## Task 11：CSV / Parquet Exporter

**任务目标：** 为下游分析导出 Silver 和 Gold datasets。

**输入文件：**

- `docs/schema.md`
- `docs/architecture.md`

**输出文件：**

- `src/jav_metadatahub/exporters/csv_exporter.py`
- `src/jav_metadatahub/exporters/parquet_exporter.py`
- export CLI command
- exporter tests

**需求：**

- 导出 core Silver tables 和 `gold_work_flat`。
- 支持 CSV 和 Parquet。
- 使用配置中的 `EXPORT_DIR`。
- 空表导出保持 graceful behavior。

**验收标准：**

- Tests 在 temporary directory 生成 CSV 和 Parquet。
- Empty-table exports 不崩溃。
- Exported columns 匹配 schema 文档。

## Task 12：FastAPI 只读 API

**任务目标：** 在 canonical entities 和 observations 之上实现 read-only API routes。

**输入文件：**

- `docs/schema.md`
- `docs/architecture.md`

**输出文件：**

- `src/jav_metadatahub/api/main.py`
- `src/jav_metadatahub/api/dependencies.py`
- `src/jav_metadatahub/api/routes/*.py`
- Pydantic response schemas
- API tests

**需求：**

- 实现 `GET /health`。
- 实现 architecture docs 中列出的 read-only work、person、company、series、tag、observation 和 source routes。
- 使用 Pydantic v2 response models。
- route handlers 不承载业务逻辑。
- list routes 支持 pagination。

**验收标准：**

- `/health` 返回 OK status。
- Route tests 使用 test database 通过。
- API surface 保持 read-only。

## Task 13：测试和文档

**任务目标：** 补齐验证覆盖，并保持文档与实现一致。

**输入文件：**

- `README.md`
- `AGENTS.md`
- `docs/*.md`
- source specs
- implemented code and tests

**输出文件：**

- 行为发生变化时更新 README 和 docs。
- 为 normalizers、parsers、repositories、services、exporters 和 API routes 补充测试。
- 使用 mocked responses 的 test fixtures。

**需求：**

- 运行 `pytest`。
- 运行 `ruff check .`。
- 运行 `ruff format --check .`。
- 运行 `mypy src`。
- 不能运行的命令说明原因，并提供最接近的验证方式。
- 保持 docs 对 V1/V2/V3 边界的描述清晰。

**验收标准：**

- Verification commands 通过，或 blockers 明确。
- README 链接到核心 docs。
- Source specs 与实现保持一致。
