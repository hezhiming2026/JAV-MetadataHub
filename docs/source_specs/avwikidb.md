# AVWikiDB 来源规格

本文档说明 AVWikiDB 在 JAV-MetadataHub 中的补充观察定位。AVWikiDB 不是 V1 主来源，后续可作为 V3 补充观察来源评估。

## 来源角色

| 属性 | 说明 |
| --- | --- |
| source name | `avwikidb` |
| 阶段 | V3 candidate |
| 来源类型 | community/wiki-style metadata source |
| 主要用途 | actor/director/CID supplement 和 selected gap filling |
| canonical authority | 默认无 |
| 采集形态 | 补充观察或人工校对工作流 |

## 可能观察字段

后续 V3 工作可观察：

- code or CID candidates
- title variants
- actor/performer supplement
- director supplement
- maker/studio supplement
- series or tag hints when visible
- source URL

观察到的字段进入 `source_records` 和 `field_observations`，再由 ingestion 规则决定后续处理。

## 推荐数据流

```text
source input
    -> source_records
    -> parser/provider
    -> field_observations
    -> candidate review
```

AVWikiDB 字段默认作为不确定补充观察。actor/director/CID 观察值可用于候选匹配和人工校对。

## 来源说明

调研文档记录 AVWikiDB 覆盖范围与稳定性证据存在差异。实现前应先确认样本、字段语义和 parser fixture。

## 测试

如果后续实现，测试使用本地 fixtures 和 mocked responses，覆盖字段解析、source record 写入、observation 写入和候选匹配。
