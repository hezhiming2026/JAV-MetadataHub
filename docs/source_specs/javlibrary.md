# JavLibrary 来源规格

本文档说明 JavLibrary 在 JAV-MetadataHub 中的补充观察定位。JavLibrary 不是 V1 主来源，后续可作为 V3 或 late V2 人工校对工作流的一部分评估。

## 来源角色

| 属性 | 说明 |
| --- | --- |
| source name | `javlibrary` |
| 阶段 | V3 candidate；late V2 可在明确需求后评估 |
| 来源类型 | community/page-style metadata source |
| 主要用途 | 长尾补充、tags、rating/review-like observations |
| canonical authority | 默认无 |
| 采集形态 | 补充观察或人工校对工作流 |

## 可能观察字段

后续工作可观察：

- code/title variants
- public actress names
- director
- maker
- label
- series when visible
- tags/community categories
- rating-like values
- review/comment metadata when available

这些字段先作为 observations 保存，后续由 explicit resolution rules 处理。

## 推荐数据流

```text
source input
    -> source_records
    -> parser/provider
    -> field_observations
    -> candidate review
```

JavLibrary 适合提供长尾作品、社区标签和评分评论类信号。它们属于来源特定信息，推荐进入 observations 或未来的 metric snapshots。

## 评分与评论说明

Ratings、reviews、comment counts、community sentiment 不是作品事实本身。建议保存为：

- source
- observed time
- source record ID
- confidence
- raw value

如需用于排序或分析，可在 metric snapshots 或 Gold 层中派生。

## 来源说明

调研文档记录 JavLibrary 的页面访问形态和社区工具实现差异。实现前应先更新样本、字段映射和测试 fixtures。

## 测试

如果后续实现，测试使用本地 fixtures 和 mocked responses，覆盖字段解析、observation 写入、rating/review 保存和冲突保留。
