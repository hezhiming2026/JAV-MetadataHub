# 数据库 Schema

本文档是 JAV-MetadataHub 的工程 schema 规格，描述预期的 PostgreSQL / SQLAlchemy / Alembic 模型，不包含 SQLAlchemy 实现代码。

## 数据分层

JAV-MetadataHub 使用三层数据模型。

| 层级 | 目标 | 主要对象 |
| --- | --- | --- |
| Bronze | 尽量少解释地保留外部来源证据。 | `collector_runs`, `source_records` |
| Silver | 将原始来源数据规范化为实体、关系、外部 ID 和字段级观察。 | `works`, `people`, `companies`, `series`, `tags`, relationship tables, `field_observations` |
| Gold | 面向分析导出和只读 API。 | materialized views, CSV, Parquet, DuckDB exports |

外部元数据的标准路径：

```text
external source
    -> source_records
    -> parser
    -> field_observations
    -> canonical entity tables
    -> gold exports / API
```

## 核心证据表

### `source_records`

`source_records` 是原始证据表，用来回答：

- 哪个来源产生了这条记录？
- 外部 key 或 URL 是什么？
- 观察到的原始 JSON、HTML、SQL-derived row 或文本是什么？
- 什么时候 fetch 或 import？
- 哪个 collector run 和 parser version 处理了它？
- 请求或导入结果是成功、失败、跳过，还是未找到？

数据架构原则：

- 来源数据在标准化前保存到这里。
- collector/import run 中出现的 failed、skipped、not-found 记录也可以保留。
- canonical 表中的值应能回溯到对应的 `source_records`。
- `raw_json` 用于 API response 和规范化后的 dump row；`raw_html` 保留给后续 HTML observation 来源。
- 可用时保留 `source`、`source_key`、`record_type`、`source_url`、`fetched_at`、`checksum` 和 `collector_run_id`。

### `field_observations`

`field_observations` 是字段证据表，用来回答：

- 哪个来源声明了某个字段值？
- 哪条 source record 支撑这个值？
- 该值的 confidence 和 observed time 是什么？
- observation 是 active、accepted、rejected 还是 superseded？
- 哪些字段在不同来源之间存在冲突？

数据架构原则：

- 不确定、冲突、来源特定或补充来源字段先保存在这里。
- canonical 字段代表当前最佳值；更新 canonical 前保留对应 observation。
- 每个提升后的 canonical 值应至少能回溯到一个 source record 和 observation。
- JavDB、JavBus、JavLibrary、AVWikiDB 等补充来源先写 observations，再由字段级规则决定是否提升。

## Canonical 字段与 Observation 字段

Canonical 字段是 Silver entity tables 上可查询、强类型的字段，表示显式规则选出的当前最佳值。

适合 canonical 的候选字段：

- 作品身份：normalized code、preferred title、release date、runtime、work type、censor type。
- 稳定关系：actress/actor/director links，maker/label/publisher/studio links，series links。
- V1 来源的稳定 external IDs：FANZA/DMM `content_id`、DMM product IDs、R18.dev `content_id` 或 `dvd_id`。

适合 observation-first 的字段：

- ratings、review counts、comments、community tags。
- translated titles 和 source-specific title variants。
- sample image URL lists 和 secondary cover URLs。
- 覆盖不稳定的 male actor data。
- alias names、retired names、language-specific names。
- site-specific flags，例如 subtitles、4K、leak labels、limited editions、version suffixes。

提升规则：

- 空的 canonical 字段可以由高置信 V1 observations 填充。
- 已有 canonical 字段通过 higher-priority sources 或 explicit resolution logic 更新。
- 冲突值保留在 `field_observations`，等待解析或人工校对。

## 核心表

schema 位于 PostgreSQL 的 `javhub` schema 下。默认使用 `BIGSERIAL` primary key，除非实现阶段选择等价 SQLAlchemy 类型。

| Table | Layer | Purpose | Primary Key | Foreign Keys | Unique Constraints | Index Recommendations |
| --- | --- | --- | --- | --- | --- | --- |
| `collector_runs` | Bronze | 记录每次 dump import、API collection、backfill 或 manual run。 | `id` | none | none required | `(source, started_at DESC)` |
| `source_records` | Bronze | 保存原始来源记录和 fetch/import 状态。 | `id` | `collector_run_id -> collector_runs.id` | `(source, source_key, record_type)` | `(source, source_key)`, `record_type`, `fetched_at DESC`, GIN on `raw_json` |
| `works` | Silver | canonical work entity。 | `id` | none | no global unique constraint on `code_norm` | `code_norm`, `(code_prefix, code_number)`, `release_date DESC`, trigram indexes on titles |
| `work_external_ids` | Silver | 映射作品到 source-specific identifiers 和 URLs。 | `id` | `work_id -> works.id`, `source_record_id -> source_records.id` | `(source, external_id, id_type)` | `work_id`, `(source, external_id)` |
| `people` | Silver | public performer、actor、director、staff entity。 | `id` | none | none required in V1 | trigram indexes on `canonical_name`, `name_ja` |
| `person_aliases` | Silver | public aliases 和 stage-name variants。 | `id` | `person_id -> people.id`, `source_record_id -> source_records.id` | `(person_id, alias, alias_type, source)` | `alias_norm`, trigram on `alias` |
| `person_external_ids` | Silver | 映射人物到 source-specific IDs。 | `id` | `person_id -> people.id`, `source_record_id -> source_records.id` | `(source, external_id, id_type)` | `person_id` |
| `work_people` | Silver | 作品-人物关系，带 role 和 provenance。 | `id` | `work_id -> works.id`, `person_id -> people.id`, `source_record_id -> source_records.id` | `(work_id, person_id, role, source)` | `(work_id, role)`, `(person_id, role)` |
| `companies` | Silver | maker、label、publisher、studio 等组织实体。 | `id` | none | none required in V1 | `name_norm`, trigram on `name` |
| `company_external_ids` | Silver | 映射公司到 source-specific IDs。 | `id` | `company_id -> companies.id`, `source_record_id -> source_records.id` | `(source, external_id, id_type)` | `company_id` |
| `work_companies` | Silver | 作品-公司关系，带 role 和 provenance。 | `id` | `work_id -> works.id`, `company_id -> companies.id`, `source_record_id -> source_records.id` | `(work_id, company_id, role, source)` | `(work_id, role)`, `(company_id, role)` |
| `series` | Silver | series entity。 | `id` | none | none required in V1 | `name_norm`, trigram on `name` |
| `series_external_ids` | Silver | 映射系列到 source-specific IDs。 | `id` | `series_id -> series.id`, `source_record_id -> source_records.id` | `(source, external_id, id_type)` | `series_id` |
| `work_series` | Silver | 作品-系列关系，带 provenance。 | `id` | `work_id -> works.id`, `series_id -> series.id`, `source_record_id -> source_records.id` | `(work_id, series_id, source)` | `work_id`, `series_id` |
| `tags` | Silver | source tags、genres、keywords 和 future governed tags。 | `id` | none | `(name_norm, tag_type, language, source)` | `name_norm`, trigram on `name` |
| `work_tags` | Silver | 作品-tag 关系，带 provenance。 | `id` | `work_id -> works.id`, `tag_id -> tags.id`, `source_record_id -> source_records.id` | `(work_id, tag_id, source)` | `work_id`, `tag_id` |
| `field_observations` | Silver | 字段级 source claims 和 conflict evidence。 | `id` | `source_record_id -> source_records.id` | none required in V1 | `(entity_type, entity_id)`, `field_name`, `source`, trigram on `field_value_text` |
| `entity_match_candidates` | Silver | 保守实体匹配候选，用于规则或人工 review。 | `id` | none generic by design | `(entity_type, left_entity_id, right_entity_id)` | `(entity_type, status)` |
| `entity_merge_logs` | Silver | accepted entity merge 的审计日志。 | `id` | none generic by design | none required | `(entity_type, from_entity_id, to_entity_id)` |
| `media_assets` | Silver | 图片、trailer、profile asset metadata；V1 保存 URL。 | `id` | `work_id -> works.id`, `person_id -> people.id`, `source_record_id -> source_records.id` | `(source, url)` | `work_id`, `person_id` |

## Gold 对象

Gold objects 是分析输出，不是权威来源证据。

推荐 Gold views 或 exports：

- `gold_work_flat`：一行一个作品，带 denormalized people、companies、series、tags。
- `gold_person_profile`：一行一个人物，带公开作品数和活动时间窗。
- `gold_company_monthly_stats`：公司月度产出指标。
- `gold_tag_monthly_trends`：tag 趋势指标。
- `gold_actor_cooccurrence`：共演图导出。
- `gold_series_lifecycle`：系列时间线和生命周期指标。

Gold exports 应能从 Bronze 和 Silver 数据复现。

## 实体解析规则

V1 的作品自动匹配可以使用：

- 相同 source external ID。
- FANZA/DMM `content_id`。
- `code_norm + maker + release_date`，前提是三者都可用且一致。

V1 的人物自动匹配可以使用：

- 相同 source person external ID。

仅同名的人物进入 `entity_match_candidates` 或人工校对流程。公司、系列和 tag 可在兼容 source/type context 下复用 normalized names；歧义情况创建 `entity_match_candidates`。

## 媒体资源规则

V1 保存 image/media URLs 和相关 metadata。`media_assets.download_status` 默认保持 `url_only`。

## Alembic / SQLAlchemy 说明

后续实现应：

- 使用 SQLAlchemy 2.x typed declarative models。
- 从本 schema spec 生成 Alembic migrations。
- 创建 `javhub` schema 和需要的 PostgreSQL extensions，例如 trigram support。
- 保留 constraints、indexes、provenance fields 和 confidence fields。
- 将来源处理逻辑接入 `source_records` 与 `field_observations`，避免形成无证据链的快捷路径。
