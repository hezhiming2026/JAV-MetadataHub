# FANZA / DMM API 来源规格

本文档说明 FANZA / DMM API 在 JAV-MetadataHub 中的 V1 接入方式。它是官方结构化元数据来源，需要配置凭证、限流、重试、日志、fixtures 和 mocked tests。

当前实现边界：已实现 client、collector、parser、observation ingestion、batch ingestion 和 CLI runner。
当前不做 canonical promotion，不创建 canonical rows。

## 来源角色

| 属性 | 说明 |
| --- | --- |
| source name | `fanza` |
| 阶段 | V1 structured API source |
| 来源类型 | official / affiliate API |
| 主要用途 | 官方元数据、增量刷新、canonical candidates |
| canonical 优先级 | 日文作品元数据和核心关系的默认最高优先级 |
| bulk access | API pagination with date windows |
| tests | mocked HTTP |

## 配置

预期 settings：

- `FANZA_BASE_URL`
- `FANZA_API_ID`
- `FANZA_AFFILIATE_ID`
- request timeout
- retry count
- default rate limit

架构草案使用的默认 base URL：

```text
https://api.dmm.com/affiliate/v3
```

凭证从 settings 或 environment variables 读取。日志和 fixtures 使用脱敏值。

## API 方法

V1 client 暴露：

- `floor_list`
- `item_list`
- `actress_search`
- `maker_search`
- `genre_search`
- `series_search`

`author_search` 可在出现明确 metadata 需求后加入。

请求参数包含：

- `api_id`
- `affiliate_id`
- `output=json`

## ItemList 参数

V1 支持参数：

| Parameter | Purpose |
| --- | --- |
| `site` | Adult/general site selector；默认支持 FANZA。 |
| `service` | 尽量来自 FloorList discovery。 |
| `floor` | 尽量来自 FloorList discovery。 |
| `keyword` | Optional search term。 |
| `cid` | Exact content ID lookup。 |
| `sort` | 默认 `date`。 |
| `hits` | Page size；使用安全默认值并尊重调研记录的限制。 |
| `offset` | Pagination offset。 |
| `gte_date` | Date-window start。 |
| `lte_date` | Date-window end。 |

## 采集策略

当前已实现到 `field_observations`，后续 canonical promotion 另行实现：

```text
FloorList discovery
    -> date-window ItemList scan
    -> paginated raw response storage in source_records
    -> parser
    -> field_observations
    -> future canonical promotion
```

使用 date windows 管理分页范围。如果一个窗口结果过大，将窗口切分为更小粒度。

## Source Key 规则

| API Field | Target | 说明 |
| --- | --- | --- |
| `content_id` | `source_records.source_key`, `work_external_ids` | FANZA source key 首选。 |
| `product_id` | `work_external_ids` | 单独保留。 |
| `maker_product` or equivalent product code | `work_external_ids`, `works.code_original` candidate | 最适合面向用户展示的番号候选。 |
| source URL / affiliate URL | `source_records.source_url`, `work_external_ids.external_url` | 保留 public source/provenance URL。 |

当 response page 包含多个 items 时，可以存 page-level `search_result` records 和 item-level `work` records，也可以先存 page-level records 再在解析阶段派生 item-level source records。选定策略需要 deterministic 并有测试覆盖。

## 字段映射

| FANZA/DMM Field / Concept | Target | Canonical Candidate | Observation Required |
| --- | --- | --- | --- |
| `content_id` | source key, external ID | yes | yes |
| `product_id` | external ID | yes | yes |
| product code / maker product | code fields, external ID | yes | yes |
| `title` | `works.title_ja` | yes | yes |
| release date / date | `works.release_date` | yes | yes |
| runtime / volume | `works.runtime_minutes` | yes, when safely parsed as minutes | yes |
| actresses | `people`, `work_people` | yes | yes |
| directors | `people`, `work_people` | yes | yes |
| maker | `companies`, `work_companies` | yes | yes |
| label | `companies`, `work_companies` | yes | yes |
| series | `series`, `work_series` | yes | yes |
| genre / keywords | `tags`, `work_tags` | source tag in V1 | yes |
| image URLs | `media_assets.url` | URL-only candidate | yes |
| review count / rating average | `field_observations` | no | yes |
| sample movie URL | `field_observations` if retained | no | yes |

## 后续 Canonical 提升规则

默认优先级：

```text
FANZA/DMM API > R18.dev dump > supplemental observations > unknown
```

FANZA/DMM observations 是后续 canonical promotion 的高优先级候选。当前实现只写
`source_records` 和 `field_observations`，不填充 canonical work fields。未来字段被提升为
canonical 时，仍应保留对应 observations，便于回溯和冲突分析。

## 限流与重试

client 包含：

- conservative default rate limit
- timeout
- retry with exponential backoff for transient failures
- 429 and 5xx handling
- structured logs
- secret redaction

重复失败时，collector 将 `collector_runs` 标记为 failed 或 partial，并记录可安全展示的失败上下文。

## 失败上下文

保存失败上下文时使用脱敏参数：

- source
- endpoint
- safe request parameters
- HTTP status
- error class/message
- retry count
- timestamp

`api_id`、`affiliate_id`、cookies、tokens、credentials 在日志和测试 fixtures 中使用 masked value。

## 测试

测试使用 mocked HTTP responses 和本地 fixtures。

必测场景：

- auth/query parameters are attached
- pagination uses expected `hits` and `offset`
- date-window parameters are passed
- retry occurs on configured transient failures
- secrets are redacted in logs
- network calls are intercepted by mocks
