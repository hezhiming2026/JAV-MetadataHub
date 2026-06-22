# JavBus 来源规格

本文档说明 JavBus 在 JAV-MetadataHub 中的补充观察定位。JavBus 不是 V1 主来源，后续可作为 V2 补充观察来源评估。

## 来源角色

| 属性 | 说明 |
| --- | --- |
| source name | `javbus` |
| 阶段 | V2 candidate |
| 来源类型 | community/page-style metadata source |
| 主要用途 | 缺失字段补充、跨来源对比 |
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
- tags
- cover URL

观察到的字段进入 `source_records` 和 `field_observations`，再由 ingestion 规则决定后续处理。

## 推荐数据流

```text
source input
    -> source_records
    -> parser/provider
    -> field_observations
    -> candidate review
```

JavBus 适合作为补充字段和交叉校验来源。canonical 更新通过明确的字段级解析规则完成。

## 来源说明

调研文档将 JavBus 视为没有 confirmed official dump/changefeed 的补充来源。实现前应先固化目标页面样本、字段选择和测试 fixtures。

## 测试

如果后续实现，测试使用本地 fixtures 和 mocked responses，覆盖字段解析、source record 写入、observation 写入和幂等行为。
