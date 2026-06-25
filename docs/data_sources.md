# 数据源说明

本文档汇总 JAV-MetadataHub 的工程数据源口径。它是面向实现的摘要文档，用来承接调研结论、来源优先级和证据链设计。

## 来源策略

V1 使用两个结构化来源：

1. `R18.dev dump`：作为冷启动、历史回填和交叉校验数据集。
2. `FANZA / DMM API`：作为官方结构化元数据入口。

V2/V3 可以逐步增加补充观察来源：

- Javinizer-Go
- MetaTube
- JavDB
- JavBus
- JavLibrary
- AVWikiDB

补充来源的定位是提供缺失字段、冲突提示或人工校对线索。外部来源数据先进入 `source_records`，再由 parser 转换为 `field_observations`；canonical 字段通过明确的解析和提升逻辑更新。

## 版本路线

| 阶段 | 来源 | 目标 | 工程定位 |
| --- | --- | --- | --- |
| V1 | R18.dev structured JSON/JSONL, FANZA/DMM API | 建立 Bronze/Silver observations 和只读 API 基础。 | 结构化来源主链路。 |
| V2 | Javinizer-Go, MetaTube, JavDB, JavBus | 增加补充观察，并对比 provider 输出。 | 补充观察、适配器或对照实现。 |
| V3 | JavLibrary, AVWikiDB, 其他来源 | 长尾补全、人工校对和分析增强。 | 补充观察和人工工作流。 |

## 来源总览

| 来源 | 字段覆盖 | 主要注意点 | 阶段 | 工程建议 |
| --- | --- | --- | --- | --- |
| R18.dev dump | 番号、标题、发行日期、时长、女优、导演、maker、分类/tag、图片 URL。 | 当前实现只支持本地 structured JSON/JSONL records；真实 `.sql` / `.sql.gz` dump 尚未实现。 | V1 | 作为可重复导入的 seed/backfill。每条导入记录进入 `source_records`，不稳定字段进入 `field_observations`。 |
| FANZA / DMM API | 番号/商品 ID、标题、发行日期、时长、女优、导演、maker、label、series、genre、图片 URL。 | 需要 API 配置；存在 credit、地域可用性和限流参数；当前不做 canonical promotion。 | V1 | 作为官方结构化 API 来源，已实现 client、collector、parser、observation ingestion 和 batch runner。 |
| Javinizer-Go | 聚合后的标题、演员、studio、series、tag、图片 URL、NFO 映射。 | 它是工具/聚合层，不是 canonical 上游。 | V2 | 可作为参考实现、兼容基线或可选内部 adapter。 |
| MetaTube | 根据 provider 返回标题、演员、导演、studio、genre、图片 URL 等。 | provider 质量不一，不是单一权威来源。 | V2 | 作为 federation/reference layer，保留 provider identity。 |
| JavDB | 番号、标题、发行日期、时长、女优、导演、maker/studio、series、tag、封面 URL、评分类信号。 | 未确认官方 dump/API；页面结构和可用性需要按版本确认。 | V2 | 作为补充观察来源。 |
| JavBus | 番号、标题、发行日期、时长、女优、导演、maker/studio、series、tag、封面 URL。 | 未确认官方 dump/API；页面稳定性和可用性需要按版本确认。 | V2 | 作为补充观察来源。 |
| JavLibrary | 番号、标题、女优、导演、maker、label、tag、评分/评论类字段。 | 社区评分和评论属于来源特定信号。 | V3 | 适合长尾补充、tag 与社区指标观察。 |
| AVWikiDB | 番号/CID 候选、演员/导演补充、作品与人物细节。 | 公开证据完整度和稳定性需要持续校验。 | V3 | 作为 selected gap filling 和人工校对来源。 |

## 后续 Canonical 来源优先级

后续字段提升优先级：

```text
FANZA/DMM API > R18.dev dump > supplemental observations > unknown
```

补充观察包括 JavDB、JavBus、JavLibrary、AVWikiDB、MetaTube、Javinizer-Go 输出。它们用于发现缺失值和冲突值，canonical 更新需要经过明确的字段级规则。

字段级说明。以下是后续 canonical promotion 的设计方向，当前实现先保存 observations：

- `title_ja`：优先使用 FANZA/DMM。
- `title_en`：R18.dev 有值时优先作为英文标题候选。
- `title_zh`：在翻译策略确定前保持 observation-first。
- `runtime_minutes`：FANZA/DMM 优先，R18.dev 用于交叉校验。
- `actress`：FANZA/DMM 优先，R18.dev 可补充。
- `actor`：V1 覆盖不稳定，优先保留观察值。
- `director`：FANZA/DMM 优先，R18.dev 可补充。
- `maker`、`label`、`series`：FANZA/DMM 有值时优先。
- `tags`：先保留 source tags；canonical tag taxonomy 是后续治理任务。
- ratings、comments、review counts、community heat、ranking signals：作为 observation 或 metric snapshots。

## V1 结构化来源

### R18.dev Dump

角色：

- 冷启动 seed。
- 历史回填。
- 跨来源校验。
- 英文标题和 legacy data 补充。

工程流程：

- 当前实现支持本地 structured JSON / JSONL records import。
- 真实 `.sql` / `.sql.gz` dump restore 和 extraction 仍是后续任务。
- 导入的 work/person/company/series/tag 记录先序列化到 `source_records`。
- 保留 dump version、observed time、checksum 和 importer version。
- source-specific 字段先进入 `field_observations`，再由 ingestion 规则决定是否提升。

### FANZA / DMM API

角色：

- 官方结构化元数据来源。
- 增量刷新来源。
- 作品身份和核心关系的高置信候选来源。

工程流程：

- 使用 async `httpx`、重试、限流、结构化日志，以及 mocked response 测试。
- 测试使用 fixtures 或 mocked HTTP。
- 日志保留请求和错误上下文，并对凭证类字段做脱敏。
- 每个原始响应页或 item response 存入 `source_records`。
- parser/ingestion flow 负责创建 observations。
- canonical promotion 仍是后续任务。

## V2/V3 补充来源

补充来源用于提升覆盖面和识别多源冲突。推荐流程：

```text
source input
    -> source_records
    -> parser/provider module
    -> field_observations
    -> candidate review / explicit promotion rule
```

`source_records` 与 `field_observations` 是所有外部来源进入系统的证据层。canonical 字段的更新应能回溯到具体来源记录和字段观察。

## 图片字段

V1 将图片、样张、预告片和人物头像作为 URL 型 metadata 保存。

图片 URL observation 建议保留：

- source
- source record ID
- observed time
- asset type
- source URL
- license/copyright note when known

## 测试说明

来源 client、importer 和 parser 使用 fixtures 与 mocked responses 覆盖。测试重点包括分页、重试、字段映射、source record 写入、observation 写入和日志脱敏。
