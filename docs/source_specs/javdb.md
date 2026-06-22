# JavDB 来源规格

本文档说明 JavDB 在 JAV-MetadataHub 中的补充观察定位。JavDB 不是 V1 主来源，后续可作为 V2 补充观察来源评估。

## 来源角色

| 属性 | 说明 |
| --- | --- |
| source name | `javdb` |
| 阶段 | V2 candidate |
| 来源类型 | community/page-style metadata source |
| 主要用途 | 缺失字段补充、冲突观察、社区信号参考 |
| canonical authority | 默认无 |
| 采集形态 | 后续按具体实现方案评估 |

## 可能观察字段

后续 V2 工作可观察：

- code/title variants
- release date
- runtime
- actresses
- director
- maker/studio
- series
- tags/community categories
- cover URL
- rating-like signals when available

观察到的字段进入 `source_records` 和 `field_observations`，再由 ingestion 规则决定后续处理。

## 推荐数据流

```text
source input
    -> source_records
    -> parser/provider
    -> field_observations
    -> candidate review
```

JavDB 字段用于补充观察和冲突提示。`works`、`people`、`companies`、`series`、`tags` 以及关系表的更新通过明确 field-level resolution logic 执行。

## 来源说明

调研文档记录 JavDB 未确认官方 public dump/API，并且页面稳定性、可用性和周边生态实现方式需要按版本复核。实现前应先更新 sample evidence 和 parser fixture。

## 测试

如果后续实现，测试使用本地 fixtures 和 mocked responses，覆盖字段解析、observation 写入、冲突保留和幂等行为。
