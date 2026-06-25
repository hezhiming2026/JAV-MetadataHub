# R18.dev Dump 来源规格

本文档说明 R18.dev dump 在 JAV-MetadataHub 中的 V1 接入方式。它是结构化 dump 来源，适合 seed、backfill 和跨来源校验。

当前实现边界：V1 importer 只支持本地 structured JSON / JSONL records。真实 `.sql` / `.sql.gz`
dump restore、staging load 和 extraction 尚未实现。

## 来源角色

| 属性 | 说明 |
| --- | --- |
| source name | `r18` |
| 阶段 | V1 structured dump source |
| 来源类型 | public structured dump |
| 主要用途 | 历史 seed、全量快照导入、英文标题补充、跨来源校验 |
| canonical 优先级 | 多数字段低于 FANZA/DMM；英文标题有值时优先作为英文标题候选 |
| bulk access | 当前为本地 JSON/JSONL import；真实 SQL dump import 待实现 |
| online JSON/API | V1 不作为 bulk 主路径 |

## 已知访问形态

调研文档记录了以下仓库内事实：

- latest dump entrypoint: `https://r18.dev/dumps/latest`
- 历史命名模式：`r18dotdev_dump_YYYY-MM-DD.sql.gz`
- 更新模式：调研时观察到 weekly dump publication。
- 文件类型：gzipped SQL dump。
- 许可说明：调研中记录 structured data 为 CC0。

实现和测试应把这些信息视作 repository-sourced research。测试使用本地 fixtures，不需要实时刷新互联网证据。

## 导入策略

当前已实现流程：

```text
local JSON/JSONL records
    -> source_records
    -> R18 parser
    -> field_observations
```

当前不支持：

- 直接读取 `.sql`。
- 直接读取 `.sql.gz`。
- 下载远程 dump。
- staging PostgreSQL restore。

后续真实 dump 支持可采用以下流程：

```text
download or provide dump file
    -> record collector_run
    -> load into staging database or staging extraction process
    -> serialize relevant source rows into source_records.raw_json
    -> parse source_records
    -> write field_observations
    -> future canonical promotion
```

importer 负责先保存来源证据，再交给 parser 和 ingestion service 写入 observations。canonical promotion
是后续任务。

## Source Key 规则

每种 record type 使用最稳定的可用 key。

| Record Type | Preferred `source_key` | 说明 |
| --- | --- | --- |
| `work` | `content_id` when available; otherwise `dvd_id` | 两者都可作为 external IDs 保留。 |
| `person` | source person ID when available | public names 和 aliases 作为 observations 保存。 |
| `company` | maker/label ID when available | 保留 maker 或 label 等 role。 |
| `series` | series ID when available | 保留 source name variants。 |
| `tag` | category/tag ID when available | 保留 language 和 source tag type。 |

缺少 key 时，可由 importer 用 source table name 和稳定 row fields 生成 deterministic importer key；生成策略需要写入 importer 代码和测试。

## 字段映射

| R18 Field / Concept | Target | Canonical Candidate | Observation Required |
| --- | --- | --- | --- |
| `dvd_id` | `works.code_original`, `work_external_ids` | yes, as code candidate | yes |
| `content_id` | `work_external_ids`, `source_records.source_key` | yes, as source identity | yes |
| Japanese title | `works.title_ja` | yes when FANZA/DMM is absent | yes |
| English title | `works.title_en` | yes, preferred when present | yes |
| release date | `works.release_date` | yes | yes |
| runtime minutes | `works.runtime_minutes` | yes, cross-check with FANZA/DMM | yes |
| actresses | `people`, `work_people` | relationship candidate | yes |
| directors | `people`, `work_people` | relationship candidate | yes |
| maker / label | `companies`, `work_companies` | relationship candidate | yes |
| series | `series`, `work_series` | relationship candidate | yes |
| categories / tags | `tags`, `work_tags` | source tag in V1 | yes |
| jacket / gallery URLs | `media_assets.url` | URL-only asset candidate | yes |
| comments/descriptions | `field_observations` | no | yes |

## 后续 Canonical 提升规则

- R18.dev 后续可在更高优先级来源缺失时填充空 canonical work fields。
- 已有 FANZA/DMM canonical 值应通过 explicit resolution rule 更新。
- FANZA/DMM 缺少英文标题时，后续可优先采用 R18.dev 的英文标题。
- Source tags 在 V1 保持 source tags；canonical tag taxonomy 是后续任务。
- 发行日期、时长、名称或关系冲突保留在 `field_observations` 中。

## 来源追溯字段

每条导入记录建议保留：

- source: `r18`
- dump version or dump date when available
- source table or record type
- source key
- source URL when available
- source record ID
- importer version
- checksum when available
- imported/fetched time
- confidence

## 失败处理

importer 在 `collector_runs` 中记录失败；如果能定位到 source record，也写入 `source_records`。

常见失败类别：

- dump file missing
- decompression failed
- staging load failed
- schema mismatch
- required key missing
- row parse failed
- relationship target missing

失败记录保留已导入的来源证据，便于重试和审计。

## 测试

测试使用本地 fixtures：

- small synthetic SQL-derived records
- serialized source rows
- parser fixtures
- importer failure fixtures
