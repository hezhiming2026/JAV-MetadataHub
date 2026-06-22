# 合规政策

本文档定义 JAV-MetadataHub 的合规边界。它基于 `README.md`、`AGENTS.md`、`docs/architecture.md` 以及 `docs/research/2026-06-21-public-metadata-sources.md` 整理而成。

## 允许的数据

JAV-MetadataHub 可以采集和处理以下公开元数据：

* 作品元数据：番号、标准化番号、标题、发行日期、时长、类型、外部 ID、公开外部 URL。
* 公开人物元数据：女优、男优、导演、工作人员角色、公开艺名、公开别名、来源 ID。
* 公司元数据：制作商、厂牌、发行商、工作室、分销商、来源 ID。
* 系列元数据。
* 标签元数据：类型、关键词、主题、来源标签名称。
* 公开来源溯源信息：来源名称、来源 key、来源 URL、置信度、抓取/导入时间、来源记录 ID。
* 在来源政策允许的情况下，原始公开 JSON、由 SQL dump 派生的行，以及未来经批准的公开 HTML 记录。


## 必需的数据流

所有外部元数据必须经过受治理的数据路径：

```text
external source
    -> source_records
    -> parser
    -> field_observations
    -> canonical entity tables
    -> gold exports / read-only API
```

合规规则：

* 原始来源证据必须在标准化之前保存。
* 不确定或存在冲突的字段必须保存为 observations。
* 补充来源不得直接覆盖 canonical 字段。
* 每个被提升的字段都应保留来源、置信度、来源记录 ID 和观测时间。
* 实体解析必须保持保守。
* 人物不得仅根据姓名进行合并。

## 来源访问政策

### V1 来源

V1 可以使用：

* R18.dev dump，作为结构化 dump 来源。
* FANZA/DMM API，作为官方结构化 API 来源。

V1 不得使用：

* JavDB 全量爬虫。
* JavBus 全量爬虫。
* JavLibrary 全量爬虫。
* AVWikiDB 全量爬虫。
* 任何第三方 HTML 全站爬虫。

### V2/V3 补充来源

JavDB、JavBus、JavLibrary 和 AVWikiDB 后续只能作为补充 observation 来源进行考虑。

未来使用必须限制在经过批准的窄范围工作流中：

* 精确番号查询。
* 手动或小批量字段补充。
* 仅作为 observation 导入。
* 在任何字段提升之前进行明确审核。


## API 和 Dump 使用原则

API client 和 dump importer 必须：

* 遵守来源条款、robots 政策、已记录的速率限制和访问限制。
* 使用保守的速率限制和重试策略。
* 记录请求和失败，但不得记录密钥。
* 将原始响应或导入记录保存到 `source_records`。
* 保留溯源信息和置信度。
* 可以通过 fixtures 和 mock responses 进行测试。
* 避免在测试中发起真实网络请求。

密钥政策：

* 不得提交 `.env`。
* 不得记录 API ID、affiliate ID、token、cookie 或凭证。
* 不得在 fixtures 中包含真实凭证。

## 图片政策

V1 存储图片 URL。

* 封面图片。
* 样张图片。
* 个人资料图片。
* 预告片。
* 任何其他媒体资源。

图片相关元数据可以作为 URL observation 存储，并包含来源、来源记录 ID、资源类型和观测时间。

## 隐私政策

允许的人物数据仅限于公开演出元数据：

* 公开艺名。
* 公开别名。
* 公开来源 ID。
* 公开角色标签，例如女优、男优、导演或工作人员。
* 真实身份推断。
* 人脸匹配。
* 人脸识别。
* 私人姓名。
* 私人地址。
* 私人联系方式。
* 私人社交账号。
* 非公开个人信息。

## 测试和 Fixtures

测试不得调用真实外部 API 或网站。

可以使用：

* 静态 fixtures。
* Mock HTTP responses。
* 本地 sample dump rows。
* 合成 records。
