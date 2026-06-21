# FANZA DMM Web Service API 深度调研与工程规格

## 核心结论

FANZA / DMM Web Service API 适合作为 JAV-MetadataHub 的 **V1 首选官方入口**，因为它具备公开、稳定、结构化的商品元数据接口，官方明确要求通过 `api_id` 与 `affiliate_id` 访问，并提供 ItemList、FloorList、ActressSearch、GenreSearch、MakerSearch、SeriesSearch、AuthorSearch 这类配套查询能力；同时，DMM 官方还提供 JavaScript、PHP、Go 三套 SDK 入口。对“只采集公开元数据、不涉及视频下载和绕过付费”的场景，这个 API 的能力边界是清晰且合规的。citeturn10search2turn10search3turn34search15turn42search2turn42search4turn44view0

从工程角度看，**ItemList 是主采集入口**，**FloorList 是配置发现入口**，**Genre/Maker/Series/ActressSearch 是维表补全入口**。完整 backfill 与增量更新都建议围绕 ItemList 做：先按 `site/service/floor` 锁定到 FANZA 成人视频域，再用 `sort=date` + `gte_date/lte_date` 做日期窗口扫描；如果某个窗口结果过大，再缩小时间窗以规避 `offset` 上限。这样既符合 API 的分页模型，也最容易实现幂等导入与断点续跑。citeturn52view1turn52view2turn52view3turn21search0turn30search0turn38search4

在字段选择上，**`content_id` 最适合作为 source_records 的 source_key**，因为 ItemList 原生支持以 `cid` 查询，响应中也稳定返回 `content_id`；而 **`maker_product` 更接近人类可读的“番号/厂商品番”**，适合进入 `work_external_ids`，但不应当替代 source 主键。`product_id` 可以并存保存，但在成人视频示例里它有时与 `content_id` 相同、并不总是等价于标准化后的“番号”展示值。citeturn19view0turn27view0turn27view2

合规上，要把它当作 **Affiliate API** 而不是匿名数据接口：官方说明 Web API 需要 DMM 会员、DMM Affiliate 注册和 API 利用注册；API 对 affiliate owner 免费开放；还要求显示 credit，并说明如果违反显示规定、改动 HTML 或图片等，可能停止 API 使用。官方帮助还明确：单次请求最多 100 条；同时存在“单位时间内请求次数”限制，但未公开具体数字，超过后会报错，因此客户端必须实现保守限流与退避重试。citeturn34search0turn34search2turn36search1turn34search1turn35search0turn30search0turn48search0turn49search0

还有一个现实约束：本次从新加坡环境调研时，DMM 的 guide、ID 确认页、credit 页都直接跳到了“该区域不可用”页面。这不等于可以断言 API 本身一定不可调用，但足以说明 **文档访问和部分站点浏览存在地域限制风险**，所以你的集成测试与生产 Collector 最好预留 JP 网络环境验证链路。citeturn55view0turn55view1turn55view2

## 官方入口与能力边界

DMM 官方首页说明，这是一套将 DMM 持有数据库对外开放的 Web API 服务；使用前需要 DMM 会员注册、DMM Affiliate 注册以及 API 利用注册。官方 guide 还写明，DMM Web API 对 DMM Affiliate owner 免费开放。支持页面进一步说明：API ID 可通过“web 服务利用注册”立即申请发放；另一个 ID 确认页说明，API ID 是每位会员 1 个，且请求里使用的 affiliate ID 必须是末尾 `990` 到 `999` 的有效 Affiliate ID，否则会报错。citeturn10search2turn10search3turn34search0turn34search2turn36search1turn10search6turn34search7

官方 API 与 SDK 的能力分层可以概括为下表。

| 类别 | 名称 | 主要用途 | 备注 |
|---|---|---|---|
| 官方查询接口 | ItemList | 商品主表检索、按关键词/日期/分类分页拉取 | 主采集入口 |
| 官方查询接口 | FloorList | 枚举站点下可用 service / floor | 配置发现入口 |
| 官方查询接口 | ActressSearch | 女优维表查询 | 适合人物补全 |
| 官方查询接口 | GenreSearch | 流派维表查询 | 需 floor_id |
| 官方查询接口 | MakerSearch | 片商维表查询 | 需 floor_id |
| 官方查询接口 | SeriesSearch | 系列维表查询 | 需 floor_id |
| 官方查询接口 | AuthorSearch | 作者维表查询 | 与 JAV 主线相关度较低 |
| 官方 SDK | JavaScript SDK | JS 客户端封装 | 官方列出，GitHub 可获取 |
| 官方 SDK | PHP SDK | PHP 客户端封装 | README 直接示范 product 查询 |
| 官方 SDK | Go SDK | Go 客户端封装 | 官方列出；社区仍常用更活跃的 go-dmm |

上表基于 DMM 官方 API 首页、guide、affiliatesdk 页面以及官方 GitHub 组织页面整理；其中官方 SDK 页面明确列出 JavaScript、PHP、Go 的下载与启动文档，PHP SDK README 还给出了 product API 的直接调用示例。citeturn10search2turn10search3turn34search15turn45search0turn42search0turn42search2turn42search4turn44view0

关于成人内容域的 `site` 值，有一个历史兼容性问题需要特别处理。较老的库与文章仍大量使用 `DMM.R18`；但 **官方 PHP SDK 的最新 release 说明已经明确写成 “Replaced DMM.R18 to FANZA”**，而较新的社区库和测试数据也都使用 `site_code=FANZA`。因此，**新实现默认应发送 `site=FANZA`，但客户端层最好兼容历史 `DMM.R18` alias 作为回退开关**。citeturn44view0turn21search0turn38search1

对 JAV-MetadataHub 而言，成人视频最关键的组合不是手写猜测，而是 **先由 FloorList 做发现，再锁定 ItemList**。官方 FloorList 参考页说明它返回站点下的 service 与 floor 结构；而公开测试数据展示了 FANZA 成人视频常见组合为 `service_code=digital`、`floor_code=videoa`、`floor_id=43`、`floor_name=ビデオ`。这意味着你的 Collector 不应把 `43/videoa` 写死在业务逻辑里，而应当在初始化阶段通过 FloorList 快照得到它，再把结果存成本地配置或维表。citeturn16search0turn41search0turn16search7turn41search1turn41search4turn41search5

## ItemList 参数与分页规则

ItemList 是 DMM 文档中的“商品搜索 API”，也是官方 SDK 中的 `ProductService` / `api("product")` 对应接口。官方与社区封装共同指向的参数集合非常稳定，包括 `site`、`service`、`floor`、`sort`、`keyword`、`cid`、`article`、`article_id`、`gte_date`、`lte_date`、`mono_stock`、`hits`、`offset`、`output`、`callback`。其中，Go 社区库 `go-dmm` 的 `ItemOptions` 与官方 Go SDK 的 `ProductService` 都把这套参数映射成强类型字段；PHP 官方 SDK README 也直接展示了 product API 调用方式。citeturn19view0turn52view1turn44view0

### 参数表

| 参数 | 是否必填 | 常见取值 | 说明 |
|---|---|---|---|
| `api_id` | 是 | 平台发放值 | API 调用身份标识 |
| `affiliate_id` | 是 | `xxx-990` 到 `xxx-999` | Affiliate 身份标识 |
| `site` | 是 | `FANZA` / `DMM.com` | 成人域与一般域切换 |
| `service` | 否 | `digital` | 建议通过 FloorList 发现 |
| `floor` | 否 | `videoa` | 建议通过 FloorList 发现 |
| `keyword` | 否 | UTF-8 关键词 | 关键词检索 |
| `hits` | 否 | `20` 到 `100` | 默认 20，单次最多 100 |
| `offset` | 否 | 从 `1` 开始 | 默认 1，最大 50000 |
| `sort` | 否 | `rank` / `date` / `review` / 价格相关值 | 建议采集时优先 `date` |
| `gte_date` | 否 | ISO8601 日期时间字符串 | 起始发布时间过滤 |
| `lte_date` | 否 | ISO8601 日期时间字符串 | 结束发布时间过滤 |
| `output` | 否 | `json` / `xml` | 工程上建议固定 `json` |
| `cid` | 否 | `1hawa00124` | 直接按 `content_id` 精确查 |
| `article` | 否 | `actress` / `author` / `genre` / `series` / `maker` | 维度过滤 |
| `article_id` | 否 | 各维表 ID | 和 `article` 配合使用 |
| `mono_stock` | 否 | `stock` / `reserve` / `mono` / `dmp` | 仅通販服务适用 |
| `callback` | 否 | 任意函数名 | `output=json` 时可输出 JSONP |

关于这个参数表，有几条是可以比较确定的：官方帮助页明确写明单次最多 100 条；帮助与社区封装都写明 `offset` 起始 1、最大 50000；官方 Go SDK 文档给出 `DefaultProductMaxOffset = 50000`、`DefaultProductMaxLength = 100`；社区封装则把 `gte_date/lte_date`、`article/article_id`、`mono_stock`、`callback` 等补齐到了工程可用层面。需要注意的是，**价格排序枚举在社区资料之间存在 `price` / `pric` / `+price` 的表述差异**，这部分官方页面因地域拦截无法在本次环境中直接验证，所以建议在 JP 网络里做一次最小化 smoke test 后再把价格排序值写死到 SDK 常量中。citeturn30search0turn21search0turn19view0turn46search1turn46search3

### 分页与增量策略

分页规则的核心很简单：**每次取 `hits` 条，从 `offset` 指定的起始位置开始**。当 `hits=100` 时，下一页就是 `offset=101`、再下一页 `201`，即“按页大小线性递增”；这一点在社区实践问答中被直接用于全量拉取，也与 `go-dmm` 里 `Next()` 通过 `nextOffset(hits, offset)` 计算下一页的实现相吻合。citeturn38search4turn53search2

但是 DMM ItemList 同时存在两个上限：**单次结果最多 100 条**，**偏移最大 50000**。因此，只靠 `offset` 深翻并不适合做特别大的全量抓取；对于 JAV-MetadataHub，更好的方法是用 `sort=date` 配合 `gte_date` / `lte_date` 做“日期窗口分页”，让单窗口内的总量永远落在可翻页范围内。如果当天或某周结果过多，就自动把时间窗切细到天、小时，直到 `total_count` 足够小为止。这属于基于官方参数模型做出的工程推论，但它能直接规避 50000 偏移上限。citeturn52view1turn52view2turn52view3turn21search0turn30search0

在速率限制上，官方支持页给出的信息是“没有公开的固定请求发送总数限制”，但又明确说明 **单位时间内的请求次数存在限制，超过会报错**。官方并未公开具体阈值，所以不要做自适应打满策略；更稳妥的做法是默认低速串行或小并发，例如 1–2 req/s 起步，收到 4xx/5xx 后做指数退避，尤其是遇到疑似限流错误时要整窗暂停重试。这里 1–2 req/s 不是官方数字，而是基于“阈值未知”的保守实现建议。citeturn48search0turn49search0

### 其他搜索接口的正确定位

FloorList、GenreSearch、MakerSearch、SeriesSearch 和 ActressSearch 不应该替代 ItemList 做主流水线。它们更适合做三件事：初始化配置、补全维表、以及将 `article/article_id` 过滤条件转成可运行查询。官方参考页和测试数据都表明，Genre/Maker/SeriesSearch 返回结果里会带 `site_code`、`service_code`、`floor_id`、`floor_code` 等上下文字段，而查询本身依赖 `floor_id`。这很适合作为 `genres`、`companies`、`series` 维表的定期刷新源。ActressSearch 则是典型的人物维表接口，返回名字、假名、三围、生日、血型、出身地、头像 URL 和各服务 listURL。citeturn10search14turn10search9turn10search16turn10search13turn51view1turn51view2turn51view3turn41search3turn41search4turn41search5

## 返回结构与字段映射

官方与开源 SDK 对 Item 响应的结构已经足够清楚。`go-dmm` 的 `Item` 结构体和 DMM 官方 Go SDK 的 `Item` / `ItemInformation` 定义表明，ItemList 的核心字段包括 `affiliateURL`、`affiliateURLsp`、`content_id`、`product_id`、`title`、`date`、`volume`、`URL`、`URLsp`、`imageURL`、`sampleImageURL`、`sampleMovieURL`、`review`、`prices`、`iteminfo` 等；其中 `iteminfo` 是一个细分维度容器，可承载 `maker`、`label`、`series`、`keyword`、`genre`、`actor`、`artist`、`author`、`director` 等数组。citeturn19view0turn14view1turn14view2turn15view2turn15view3

但对 JAV 领域真正重要的是：**成人视频公开样例里，`iteminfo` 实际常见的是 `genre`、`maker`、`actress`、`director`、`label`、`series`**；而在这批可见样例里，并没有出现 `actor`。这意味着“男优”字段不能假定来自 DMM API 的稳定主字段，只能作为可选 observation；相反，女优、制作商、导演、厂牌、系列、流派的覆盖是相对明确的。citeturn28view0turn28view1turn28view2turn28view3turn29view0

### 字段映射表

| 目标字段 | DMM 路径 | 建议落库方式 | 备注 |
|---|---|---|---|
| `source_key` | `content_id` | `source_records.source_key` | DMM 源内主键首选 |
| `external_id:dmm_content_id` | `content_id` | `work_external_ids` | 与 source_key 同值也可保留 |
| `external_id:dmm_product_id` | `product_id` | `work_external_ids` | 保留，但不作源主键 |
| `external_id:maker_product_code` | `maker_product` | `work_external_ids` | 最接近“番号/品番” |
| `title` | `title` | canonical candidate + observation | 原样保存，同时可做清洗版本 |
| `release_at_raw` | `date` | field_observations | 原始时间戳字符串 |
| `release_date` | `date[:10]` | canonical candidate | 仅取日期部分 |
| `runtime_minutes_raw` | `volume` | field_observations | 原始字符串 |
| `runtime_minutes` | `volume` | canonical candidate | 仅当 floor 为视频时解析为整数 |
| `actresses` | `iteminfo.actress[]` | 关系表 | 常见且重要 |
| `actors_male` | `iteminfo.actor[]` | field_observations 为主 | 成人视频样例覆盖不稳定 |
| `directors` | `iteminfo.director[]` | 关系表 | 可用 |
| `maker` | `iteminfo.maker[]` | 关系表 | 可用 |
| `label` | `iteminfo.label[]` | 关系表 | 可用 |
| `publisher` | 无明确一等字段 | 不建议强行映射 | DMM v3 schema 不清晰 |
| `series` | `iteminfo.series[]` | 关系表 | 可用 |
| `genres` | `iteminfo.genre[]` | 关系表 | 可用 |
| `cover_urls` | `imageURL.list/small/large` | `work_images` | 建议保存多尺寸 |
| `sample_image_urls` | `sampleImageURL.sample_s.image[]` | `work_images` | 数组 |
| `sample_movie_urls` | `sampleMovieURL.*` | observations | 不是你当前主需求，但可留痕 |
| `rating_count` | `review.count` | `work_ratings` | 有 |
| `rating_average` | `review.average` | `work_ratings` | 有 |
| `review_text` | 无 | 不支持 | DMM 不返回评论正文 |
| `comment_blurb` | `comment` | observations | 是商品描述片段，不是用户评论 |

上表的判断依据主要来自 DMM 官方 Go SDK 类型定义、社区 `go-dmm` 的 Item 结构，以及公开测试数据里的成人视频样例。特别要注意三点：其一，`review` 只有 `count` 与 `average`，**没有评论正文**；其二，`date` 是完整日期时间串，成人视频样例是 `YYYY-MM-DD HH:MM:SS`；其三，`volume` 在视频样例里表现为分钟数字字符串，但从 API 命名看它本质是原始来源字段，不保证在所有 floor 都等价于“片长分钟”。citeturn15view2turn27view0turn28view0turn19view0

### 哪些字段适合做 canonical 主字段

如果你的目标是以后把 DMM、R18.dev、JavDB、JavBus 等源合并成统一底座，那么在 **DMM 单源导入阶段**，我建议把下列字段定义为 “canonical candidate”，而不是无条件“唯一真相”：`title`、`release_date`、`runtime_minutes`、`actresses`、`directors`、`maker`、`label`、`series`、`genres`、`cover_urls`。这些字段在 DMM 的响应结构里有明确路径，且成人视频示例里有较强覆盖。citeturn14view1turn14view2turn27view0turn28view1turn28view2turn28view3

相反，**更适合只进入 `field_observations`** 的字段包括：`content_id`、`product_id`、`maker_product` 的原始大小写与连字符形式、`date` 的完整时间串、`volume` 原始字符串、`comment`、`URL`/`affiliateURL`、`sampleMovieURL`、以及任何 `iteminfo` 里不稳定出现的 bucket。原因很简单：这些值要么是“来源侧主键”，要么是“来源侧展示/检索辅助字段”，要么覆盖并不稳定，直接上升为全局 canonical 很容易污染跨源对齐逻辑。citeturn19view0turn27view3turn28view0turn29view0

### 样例 JSON 结构

下面这个样例是**按官方与公开测试结构整理的“实现用骨架”**，字段名与层级可直接给 Codex 用于定义反序列化模型；值用占位符替代，以避免把测试样例硬编码进实现。其结构依据来自 Item、ItemInformation、ImageURL、SampleImageURL、Review 等公开定义与测试夹具。citeturn14view1turn14view2turn15view1turn15view2turn27view0turn27view1

```json
{
  "request": {
    "parameters": {
      "api_id": "<api_id>",
      "affiliate_id": "<affiliate_id>",
      "site": "FANZA",
      "service": "digital",
      "floor": "videoa",
      "hits": "100",
      "offset": "1",
      "sort": "date",
      "output": "json"
    }
  },
  "result": {
    "status": "200",
    "result_count": 100,
    "total_count": "<total_count>",
    "first_position": 1,
    "items": [
      {
        "content_id": "<content_id>",
        "product_id": "<product_id>",
        "maker_product": "<maker_product>",
        "title": "<title>",
        "date": "YYYY-MM-DD HH:MM:SS",
        "volume": "<runtime_or_volume>",
        "URL": "https://www.dmm.co.jp/...",
        "affiliateURL": "https://www.dmm.co.jp/.../<affiliate>",
        "imageURL": {
          "list": "https://pics.dmm.co.jp/...pt.jpg",
          "small": "https://pics.dmm.co.jp/...ps.jpg",
          "large": "https://pics.dmm.co.jp/...pl.jpg"
        },
        "sampleImageURL": {
          "sample_s": {
            "image": [
              "https://pics.dmm.co.jp/...-1.jpg",
              "https://pics.dmm.co.jp/...-2.jpg"
            ]
          }
        },
        "review": {
          "count": 5,
          "average": "3.60"
        },
        "prices": {
          "price": "<display_price>",
          "list_price": "<list_price>",
          "deliveries": {
            "delivery": [
              { "type": "stream", "price": "<price>" },
              { "type": "download", "price": "<price>" }
            ]
          }
        },
        "iteminfo": {
          "genre": [{ "id": "<genre_id>", "name": "<genre_name>" }],
          "maker": [{ "id": "<maker_id>", "name": "<maker_name>" }],
          "label": [{ "id": "<label_id>", "name": "<label_name>" }],
          "series": [{ "id": "<series_id>", "name": "<series_name>" }],
          "actress": [{ "id": "<actress_id>", "name": "<actress_name>" }],
          "director": [{ "id": "<director_id>", "name": "<director_name>" }]
        }
      }
    ]
  }
}
```

## 工程规格草案

### 适合 `docs/source_specs/fanza_dmm_api.md` 的规格

**Source name**: `fanza_dmm_api`  
**Source class**: official affiliate API  
**Primary fetch endpoint**: ItemList  
**Auxiliary endpoints**: FloorList, ActressSearch, GenreSearch, MakerSearch, SeriesSearch, AuthorSearch  
**Default adult target**: discover via FloorList, then prefer `site=FANZA`, `service=digital`, `floor=videoa` for mainstream adult video collection.citeturn16search0turn41search0turn16search7turn44view0

**Auth / registration**  
Requires DMM member account, DMM Affiliate account, and API registration. `api_id` is issued by API registration; `affiliate_id` must be the registrant’s valid affiliate ID and requests only work for affiliate IDs ending in `990`–`999`.citeturn34search0turn10search3turn36search1turn34search7

**Request defaults**  
Use `output=json`. Default `site=FANZA`. Resolve `service/floor` from cached FloorList snapshot instead of hardcoding. For collector jobs, default `sort=date`; for point lookup, use `cid=<content_id>`.citeturn19view0turn16search0turn41search0

**Pagination**  
Use `hits=100` for throughput. First page is `offset=1`; subsequent pages increment by `hits`. Enforce client-side ceiling `offset <= 50000`. If a date window still overflows that ceiling, split window recursively.citeturn30search0turn21search0turn38search4

**Incremental strategy**  
Maintain a high-water mark on DMM `date` in UTC-naive source time. Pull overlapping windows using `gte_date` / `lte_date`; overlap by at least 1 day to absorb late catalog changes; dedupe by `content_id`. Because `date` is a full timestamp string, persist raw value in `field_observations` and derive normalized `release_date` separately.这里的“重叠窗口”是工程建议，不是官方规则。citeturn52view1turn52view2turn52view3turn27view0

**Identity mapping**  
- `source_records.source_key = content_id`
- `work_external_ids`: `dmm_content_id`, `dmm_product_id`, `maker_product_code`
- optional person/company external IDs from auxiliary APIs: `dmm_actress_id`, `dmm_maker_id`, `dmm_series_id`, `dmm_genre_id`。citeturn19view0turn27view0turn41search3turn41search4turn41search5

**Parser rules**  
- `title`: raw string  
- `release_at_raw`: full `date` string  
- `release_date`: first 10 chars of `date` if parseable  
- `runtime_minutes`: parse `volume` to integer only when target floor is video  
- `actresses/directors/maker/label/series/genres`: from `iteminfo` buckets  
- `publisher`: leave null unless another source corroborates  
- `review_average` / `review_count`: map from `review`  
- `review_text`: unsupported  
- `cover_urls`: `imageURL.list/small/large`  
- `sample_image_urls`: flatten `sampleImageURL.sample_s.image[]`。citeturn14view1turn14view2turn15view1turn15view2turn27view0turn27view1

**Error handling**  
Treat HTTP/network failure, parse failure, and API-level bad request separately. Public examples show invalid requests can return status `400` with field-level `errors` payload; official support pages additionally confirm throttling-like errors can happen when request count in a time window is exceeded. Recommended retry policy: exponential backoff with jitter for network / transient failures; no blind retry for parameter validation errors; pause-and-retry for suspected rate limits.citeturn38search3turn48search0turn49search0

**Compliance**  
Display required DMM credit anywhere the API powers a site or app. Do not alter provider HTML or images in ways prohibited by their display rules. Because DMM Affiliate has dedicated “image use rules” and “image restrictions” pages, the safest importer policy is: store remote URLs and downloaded metadata, but only mirror or republish images after an explicit compliance review in a JP-accessible environment. This is a conservative engineering inference from the official rules pages.citeturn34search1turn35search0turn34search3turn34search4

### FanzaClient 方法设计

下面是更适合 Codex 直接落地的接口轮廓。它不依赖某门语言，但会贴近你后续写 Python / Go / TypeScript 都容易映射的抽象。

| 方法 | 作用 | 输入 | 输出 |
|---|---|---|---|
| `get_floor_tree()` | 拉取并缓存 FloorList | 无 | floor tree DTO |
| `resolve_adult_video_floor()` | 从 floor tree 解析 FANZA 视频 floor | 可选策略参数 | `{site, service, floor, floor_id}` |
| `list_items(params)` | 调用 ItemList 原始接口 | ItemListParams | Raw JSON |
| `list_items_by_date_window(start, end, offset)` | 日期窗分页拉取 | 时间窗 + offset | Raw page |
| `get_item_by_cid(cid)` | 精确定位单个内容 | `content_id` | item or null |
| `list_genres(floor_id, ...)` | 维表刷新 | `floor_id` | genre DTO list |
| `list_makers(floor_id, ...)` | 维表刷新 | `floor_id` | maker DTO list |
| `list_series(floor_id, ...)` | 维表刷新 | `floor_id` | series DTO list |
| `search_actresses(...)` | 人物补全 | keyword / initial 等 | actress DTO list |
| `parse_item(raw)` | 原始 item -> 领域模型 | raw item | normalized record |
| `parse_page(raw_page)` | 原始 page -> page model | raw page | `{items, page_info}` |

这个方法集合的依据，是官方 endpoint 列表、官方 SDK 的 service 划分，以及社区 `go-dmm` 把 `Items`、`Genres`、`Makers`、`Series`、`Actresses` 拆成不同 service 的做法。citeturn44view0turn42search2turn19view0turn53search1

### Collector 分页策略

推荐的 Collector 逻辑是：

先调用 `get_floor_tree()`，解析出 FANZA 成人视频目标 floor；然后以“月”为初始粒度执行日期窗口扫描；每个窗口内按 `offset=1, 101, 201...` 翻页；如果 `total_count` 逼近深分页风险，就把窗口缩小到周、日甚至小时。这样设计，是因为官方允许 `gte_date` / `lte_date` 过滤，又把 `offset` 上限卡到 50000，所以窗口切分比无限深翻更稳。citeturn52view1turn52view2turn52view3turn21search0turn38search4

增量更新时，不要只依赖“今天以后”的窗口。由于源站目录可能补录、延期、改标题或改封面，建议用 **滚动重扫**：例如每天重扫最近 7–14 天，每周再重扫最近 90 天。这个部分是工程经验型建议，但与 DMM 返回完整 `date` 字段且允许日期过滤的 API 模型是兼容的。citeturn27view0turn52view2turn52view3

### Parser 字段决策

`content_id` 是源内最稳定的抓取锚点，因为 ItemList 直接提供 `cid` 精确过滤入口；`maker_product` 是对最终用户最有意义的“品番候选”；`product_id` 则建议作为兼容性 ID 保留。对标题、片长、人物和分类，建议保留 **raw value + normalized value** 双轨：raw 进 `field_observations`，normalized 进候选 canonical。这样可以为后续多源裁决留下空间。citeturn19view0turn27view0turn27view2

### source_records 与 external IDs 建议

推荐如下：

- `source_records`
  - `source_name = "fanza_dmm_api"`
  - `source_key = <content_id>`
  - `fetched_at`
  - `raw_payload_json`
  - `page_meta_json`
- `work_external_ids`
  - `id_type = "dmm_content_id"`
  - `id_type = "dmm_product_id"`
  - `id_type = "maker_product_code"`

这样做的好处，是把“源主键”和“跨源人类可读代码”拆开处理，既能保证幂等，也不妨碍后续把 `maker_product_code` 与其他站点的展示番号对齐。citeturn19view0turn27view0turn27view2

## 合规约束与任务清单

### 使用限制与合规风险

DMM Web API 并不是“无身份公共 API”，它属于 Affiliate 体系。官方首页与 guide 已经把注册前提写清楚；credit 页面说明使用 API 制作的网站或应用需要显示 credit；同页还明确写到，若不遵守显示规定、对 HTML 或图片实施改动等，可能停止 API 使用。对你的项目来说，这意味着：**内部数据底座可以用，但如果对外展示基于 DMM API 的页面或 App，必须把 credit 与使用规范作为发布门槛**。citeturn34search0turn34search2turn34search1turn35search0

官方还有单独的“图片利用规则”“图片利用限制”页面，说明 Affiliate 对图片使用是有专门规则的。因此，在元数据底座设计里，最保守的做法不是大规模再分发图片文件，而是优先存储图片 URL、尺寸、校验信息与抓取时间；如确需镜像缓存，也应该把它做成可关闭功能，并在上线前完成一次基于官方规则的法务/合规复核。这里最后一句是工程建议。citeturn34search3turn34search4

另外，`affiliate.dmm.com` 的 `robots.txt` 对多类参考页、广告工具页和部分 archive 路径标了 `Disallow`。这并不否定 API 本身的合法使用，因为官方本来就提供了机器使用的 API 接口；但它说明 **不应把 HTML 页面抓取当成主线路**。对 JAV-MetadataHub 来说，正确路径就是“优先 API，不爬前台 HTML”。citeturn33view0turn10search2

### 推荐给 Codex 的实现任务清单

下面这份清单可以直接拆成 issue 或 PR 任务：

- 实现 `FanzaClient` 基础 HTTP 层：认证参数注入、超时、重试、限流、错误分类。依据是官方必须携带 `api_id` / `affiliate_id`，且帮助文档确认存在时间窗内请求限制。citeturn34search0turn34search7turn48search0turn49search0
- 实现 `FloorList` discovery，并把 `site/service/floor/floor_id` 持久化到本地配置表，禁止业务代码硬编码 `videoa/43`。citeturn16search0turn41search0turn16search7
- 实现 `ItemListParams` 强类型模型，覆盖 `site/service/floor/keyword/hits/offset/sort/gte_date/lte_date/output/cid/article/article_id/mono_stock/callback`。citeturn19view0turn52view1
- 实现 `DateWindowCollector`：月窗扫描、超量自动切窗、`offset` 深翻、断点续跑。citeturn21search0turn30search0turn38search4
- 实现 `ItemParser`：把 `content_id/product_id/maker_product/title/date/volume/iteminfo/review/imageURL/sampleImageURL` 映射到领域对象与 observation。citeturn14view1turn14view2turn15view2turn27view0turn27view1
- 定义 `source_records` 与 `work_external_ids` 写入策略：`source_key=content_id`，external IDs 至少包含 `dmm_content_id`、`dmm_product_id`、`maker_product_code`。citeturn19view0turn27view0turn27view2
- 实现 `GenreSearch`、`MakerSearch`、`SeriesSearch`、`ActressSearch` 的维表同步 job。citeturn10search9turn10search16turn10search13turn51view1
- 增加 `site value compatibility`：默认 `FANZA`，但保留历史 `DMM.R18` 兼容配置项。citeturn44view0turn21search0turn38search1
- 增加发布层合规检查：若项目启用对外展示，则必须配置 DMM credit；若启用图片镜像，则必须显式确认图片规则。citeturn34search1turn35search0turn34search3turn34search4
- 在 CI 中加入一条“JP 网络验证”流水线，因为本次调研环境下官方 guide / credit / ID 页面存在区域不可用提示。citeturn55view0turn55view1turn55view2

### 最终推荐架构

对于 JAV-MetadataHub 的 FANZA/DMM 接入，我建议采用 **三层式架构**：最底层是 `raw source ingestion`，负责稳定、低速、幂等地拉取 ItemList 与维表接口并保存原始 JSON；中间层是 `normalization + observations`，把 DMM 字段映射到统一 schema，同时保留所有 raw values；最上层才是 `canonical reconciliation`，在未来与 R18.dev、JavDB、JavLibrary 等数据源做交叉对齐。这样，DMM 既能作为 V1 官方种子源，也不会在后续多源融合时把“源内主键”误判成“全局真相”。这一架构判断是基于 DMM API 已经提供较高质量结构化元数据、但仍存在字段稳定性与覆盖边界差异这一事实作出的工程结论。citeturn19view0turn14view1turn14view2turn28view1turn28view2turn28view3