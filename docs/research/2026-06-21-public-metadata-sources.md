# 日本 AV 公开元数据底座可用数据源调研报告

## 研究范围与结论摘要

本报告只讨论**公开元数据**的采集、治理与工程接入；视频本体、磁力、破解、付费内容处理和非公开个人数据不在研究范围内。研究重点放在你列出的九类来源，并优先采用官方文档、官方站点、GitHub 仓库、项目 Wiki、发布说明与活跃维护项目作为证据。需要先说明一点：部分站点在当前环境下存在**地域限制**或**访问稳定性机制**，例如 DMM Web API 官方页面会直接返回“当前地区不可用”，JavLibrary、JavDB 等也被多个活跃项目明确标注为需要 Cloudflare 相关处理或人工会话；因此，某些字段覆盖结论只能基于“官方信息 + 活跃 OSS 适配器”的交叉验证，而不能把它们当成完全稳定的官方承诺。citeturn41view0turn42view0turn19view0turn49view0turn58view0

如果目标是建设一个面向后续分析的 **JAV-MetadataHub**，我给出的核心结论是：**V1 应以 FANZA/DMM Web Service API 与 R18.dev dump 为主底座，Javinizer-Go 或 MetaTube 作为适配/参考实现而不是权威上游；JavLibrary、JavDB、JavBus、AVWikiDB 应作为补充型 observation 来源，而不是一开始就当成 canonical truth。**原因很直接：DMM 是官方 API 入口，R18.dev 明确提供结构化 JSON 访问与周度 dump，且声明“全部结构化数据使用 CC0”；相比之下，JavLibrary/JavDB/JavBus 多数只能从 HTML 页面或社区 wrapper 间接接入，稳定性和 ToS 不确定性都明显更高。citeturn40search0turn52search0turn8view0turn9view0turn19view0turn55view0

从工程视角看，最合理的路线不是“先做一个巨大的全字段主表”，而是做成**多源 observation 仓 + 规则提升的 canonical 层**。这个判断并不是抽象架构偏好，而是由现有生态决定的：Javinizer 强调可 mix-and-match 多个 scraper 的字段，Javinizer-Go 明确支持多源抓取、批量处理、NFO 输出与 API/Web UI，MetaTube 则把“provider 优先级”“按 provider 过滤”“查看已启用 provider 列表”都做成了产品能力。换句话说，**多源冲突是常态，不是边角问题**。citeturn16view0turn19view0turn55view0turn56view0

## 数据源总览表

下表给出面向工程实现的总览。这里的“公开 API / dump / SDK / GitHub 项目”是指本轮公开证据中可确认的能力；“批量”“增量”强调**工程可操作性**，不是法律许可结论。

| 数据源 | 类型 | 公开 API / dump / SDK / GitHub 项目 | 批量采集可行性 | 增量更新可行性 | 使用限制与访问稳定性 | 综合建议 |
|---|---|---|---|---|---|---|
| FANZA / DMM Web Service API | 官方 API | 有官方 Web API；需 API ID / Affiliate ID，且官方文档提示 Affiliate ID 末尾需为 990–999；社区项目也明确“直连 dmmapi 需要开通 dmm affiliate”。citeturn52search0turn40search0turn53search6 | 高。最适合程序化、结构化采集。citeturn52search0turn53search6 | 中。公开证据未见官方 changefeed；建议按发布日期窗口重扫最近区间。citeturn52search0turn53search6 | 中。存在地域限制，且 API 带有联盟/信用展示约束。citeturn41view0turn42view0turn0search3 | **优先级最高** |
| R18.dev | 公开结构化数据站点 + dump | 有 JSON 形式详情入口证据、周度 dump、历史 dump 目录，且声明“全部结构化数据为 CC0”。citeturn7search0turn8view0turn9view0 | 很高。周度 dump 适合冷启动全量导入。citeturn9view0 | 很高。可按周 dump 做 diff；也可按编号回查 JSON。citeturn7search0turn9view0 | 中。2025 年社区曾报告搜索与 URL 抓取出现 403，但 dump 路线仍被社区拿来继续使用。citeturn60search3turn60search1 | **优先级最高** |
| Javinizer | OSS 聚合抓取与 NFO 生成 | 有 GitHub 项目；旧项目已归档，作者明确建议迁移到 Javinizer-Go。支持多源 mix-and-match 与 NFO。citeturn16view0turn15view0 | 作为“采集框架”可行，但不宜当权威源。citeturn16view0 | 中。可做批任务，但本质依赖上游源稳定性。citeturn16view0 | 中高。依赖多站点 scraper，受上游页面变化影响。citeturn16view0turn34search1 | 适合作为参考实现与兼容层 |
| Javinizer-Go | OSS 聚合抓取、API、Web UI、批任务 | 有 GitHub 项目、持续发布、内置 CLI/TUI/API/Web UI、Swagger、批 job API 迹象。citeturn19view0turn57view0turn18search16 | 高。更现代，适合批量整理/抓取工作流。citeturn19view0turn57view0 | 中高。可以围绕 batch job / re-scrape / recent horizon 做。citeturn57view0 | 中高。仍受 R18.dev、JavLibrary、JavDB 等上游可用性影响。citeturn19view0turn57view0 | **优先级高，作为接入层而非主源** |
| MetaTube / metatube-server | OSS 后端 API 聚合层 | 有官方社区主页、Wiki、/v1/providers、provider 优先级、20+ provider、RESTful API、SQLite/PostgreSQL。citeturn56view0turn55view0turn22search1 | 高。适合作为 federation / 兼容层。citeturn56view0turn55view0 | 中高。取决于 provider 与本地数据库同步策略。citeturn56view0turn22search1 | 中高。不是权威上游，且 provider 质量不一致，官方文档也明确提醒第三方源可能不准确或缺失。citeturn55view0 | **优先级高，作为可插拔增强层** |
| JavLibrary | 社区数据库 / 页面型源 | 未见官方 API；社区 wrapper 提供 detail / comments / reviews / maker / label / director / tag / star 等接口，但明确要求手工 session / Cookie，并要跨过 Cloudflare。citeturn49view0turn34search1turn58view0 | 低到中。纯自动批量抓取不稳，OpenAver 甚至把它限制为手动、精确番号、桌面真人模式。citeturn58view0 | 低。没有公开 dump / changefeed。citeturn49view0 | 高。Cloudflare、人机验证、会话 Cookie 都是实锤。citeturn49view0turn34search1turn58view0 | **只适合补标签、评分、长尾番号** |
| JavDB | 社区数据库 / 页面型源 | 未见官方 API；活跃 scraper 与 Javinizer-Go 均将其作为 HTML 源接入，并提到可结合 FlareSolverr。citeturn19view0turn50search1turn33search1 | 中。可做受控补抓，但不适合一上来做全量。citeturn19view0turn50search1 | 低到中。没有公开 dump / 官方增量接口证据。citeturn19view0turn50search1 | 高。Cloudflare / 代理友好 / 站点防护在生态里是常识性问题。citeturn19view0turn34search8 | **补充源** |
| JavBus | 社区数据库 / 页面型源 | 未见官方 API；多语言页面常被 scraper 使用。citeturn19view0turn50search1turn53search7 | 中。可做 код-seeded 精确抓取。citeturn50search1turn53search7 | 低到中。无公开 dump / changefeed 证据。citeturn50search1 | 中高。需要代理/站点稳定性监控。citeturn34search8turn59view0 | **补充源** |
| AVWikiDB | 社区 wiki / 页面型源 | 本轮未检到官方 API / dump；社区 issue 认为可通过 `/work/<番号>/` 直接查，且一度被描述为“无 cf 墙”，但另一活跃项目 changelog 又写明它存在 Cloudflare、可取到 CID、可查男优且没有故事简介。说明其可用性与页面行为在变化。citeturn36search1turn51search1 | 中低。适合精确补抓，不适合把它当首批全量底座。citeturn36search1turn51search1 | 低。无 dump / API 证据。citeturn36search1turn51search1 | 中到高。证据本身互相冲突，说明稳定性要打折。citeturn36search1turn51search1 | **观察性接入** |

就“底座”二字而言，真正能支撑冷启动全量、后续治理、并适合交给 Codex 做工程落地的，只有两类：**官方 API** 与 **可验证的 dump**。在当前研究范围内，最符合这个标准的是 DMM/FANZA API 与 R18.dev dump；其余来源更像“补洞层”或“冲突观察层”。citeturn52search0turn8view0turn9view0turn55view0

## 字段覆盖矩阵

下面的矩阵使用三档标记：**✓ 已在本轮证据中明确确认**，**△ 仅能从活跃 scraper / 聚合器间接确认，或取决于 provider / 站点页面**，**— 本轮未确认，不建议在 V1 作为依赖字段**。  
其中，Javinizer / Javinizer-Go / MetaTube 是**聚合层**，不是源站本身，所以它们的“覆盖”表示“可经其聚合输出”，不是“原生权威字段”。

| 数据源 | 番号 | 标题 | 发行日期 | 时长 | 女优 | 男优 | 导演 | maker | label | publisher | series | genre/tags | 封面/样张 URL | 评分/评论 | 证据说明 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| FANZA / DMM API | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | — | 官方 API 公开存在；活跃 DMM scraper / SDK 可确认 `number/title/release/runtime/actors/director/series/studio(tags)/fanart` 等，但本轮未见能稳定证明 label/publisher/rating/comment 的官方字段证据。citeturn52search0turn53search7turn53search6 |
| R18.dev | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | — | ✓ | ✓ | — | 官方样例 JSON 可直观看到 `title/release_date/runtime_mins/actresses/directors/jacket_full_url/gallery/categories`，dump 页声明全部结构化数据 CC0。citeturn7search0turn8view0turn9view0 |
| Javinizer | ✓ | ✓ | ✓ | ✓ | ✓ | △ | ✓ | ✓ | △ | △ | ✓ | ✓ | ✓ | △ | 作为多源聚合/NFO 输出工具，可从 JavLibrary、R18、DMM、JavBus 等混合抓取；评分、评论、publisher 等是否可得取决于上游。citeturn16view0 |
| Javinizer-Go | ✓ | ✓ | ✓ | ✓ | ✓ | △ | ✓ | ✓ | △ | △ | ✓ | ✓ | ✓ | △ | README 明确支持多源 scraping、媒体下载、NFO、API/Web UI；JavLibrary rating 与 R18/DMM 截图回退逻辑也直接出现在 release notes 中。citeturn19view0turn57view0 |
| MetaTube / metatube-server | ✓ | ✓ | △ | △ | ✓ | △ | ✓ | ✓ | △ | △ | △ | ✓ | ✓ | △ | 官方文档明确说它用后端 API server 输出 JSON；插件特性明确包括 title / genres / director / actors / studio / trailer；其余字段取决于 provider。citeturn56view0turn21search1turn22search1 |
| JavLibrary | ✓ | ✓ | △ | △ | ✓ | — | ✓ | ✓ | ✓ | — | △ | ✓ | △ | ✓ | 社区 wrapper 明确提供 `getVideoDetail/getVideoComments/getVideoReviews/listByDirector/listByLabel/listByMaker/listByTag/listByStar`，Javinizer-Go release 还直接提到“抽取 javlibrary rating”。citeturn49view0turn57view0 |
| JavDB | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | △ | 活跃 Go scraper 文档明确有 `GetNumber/GetTitle/GetRelease/GetRuntime/GetActors/GetDirector/GetSeries/GetStudio/GetTags/GetCover`；另有项目把 JavDB 明确描述为可提供 titles / covers / cast / ratings。citeturn50search1turn33search1turn48search12 |
| JavBus | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | — | 活跃 Go scraper 文档明确有 `GetNumber/GetTitle/GetRelease/GetRuntime/GetActors/GetDirector/GetSeries/GetStudio/GetTags/GetCover`；本轮未找到其评分/评论的强证据。citeturn50search1turn53search7 |
| AVWikiDB | ✓ | △ | △ | △ | △ | ✓ | △ | △ | — | — | △ | △ | △ | — | 社区证据表明它可通过 `/work/<番号>/` 直接按番号访问；另一个活跃项目纪录显示它能拿到 CID、可查男优，但“没有作品故事介绍”，并提到 Cloudflare。说明字段能见度存在，但稳定性与完整性不足。citeturn36search1turn51search1 |

对你要做“元数据底座”这件事，最关键的不是“谁字段最多”，而是“谁的字段最适合晋升为主字段”。从这个角度看，**番号、标题、发布日期、时长、女优关系、厂牌层级、封面主图**最适合作为 canonical；**评分、评论、社区标签、翻译标题、样张列表、男优、别名**则更适合作为 observation 或可选二级字段，因为它们在上游覆盖明显不均、来源之间的冲突也更频繁。这个判断与多源项目的设计高度一致：Javinizer / Javinizer-Go 都是把多个源混合后再输出，MetaTube 甚至把 provider 优先级与过滤公开暴露出来。citeturn16view0turn19view0turn55view0turn59view0

## 工程接入与来源评估

### 批量采集与增量更新

**DMM/FANZA API** 最适合做程序化接入，但公开证据没有显示它提供一个现成的“变更流”或“最近修改列表”给你直接消费，所以更现实的做法是按**发布日期窗口**或**编号分段**做重扫，最近一段时间高频回刷，历史区间低频回刷。它适合做在线补全，也适合做“新作品滚动采集”，但不如 dump 那样天然适合大规模审计与可追溯快照。citeturn52search0turn53search6

**R18.dev** 则非常像专门为“底座工程”准备过的来源：站点直接提供 JSON 风格详情样例，dump 页又公开了 latest dump 与按日期排列的历史 dump，并声明所有结构化数据 CC0。工程上，这意味着你完全可以做出 `full snapshot + weekly diff + provenance hash` 的一套标准仓储流程；冷启动时导一次全量，之后每周下新 dump 做主键 diff 与字段级 diff。citeturn7search0turn8view0turn9view0

**JavLibrary / JavDB / JavBus / AVWikiDB** 更适合作为目标明确的补充观察来源。JavLibrary 的问题最明确：多个项目都显示它被 Cloudflare challenge 保护，OpenAver 甚至专门把它限制为“桌面真人、精确番号、不可批量、不可给 AI 代理使用”的 BETA 模式；这实际上已经给了你一个很有价值的工程信号：**这类源更适合作为人工触发的补录通道，而不是底座主流水线**。JavDB 也被 Javinizer-Go 标记为可用 FlareSolverr 的 provider；JavScraper 插件则明确要求通过 jsproxy 或代理访问若干站点。AVWikiDB 目前公开证据互相冲突，更说明它适合放在 observation lane。citeturn49view0turn34search1turn58view0turn19view0turn34search8turn36search1turn51search1

### 使用限制、ToS、robots 与访问稳定性

DMM/FANZA 的风险主要是**契约型限制**而不是技术型障碍。官方结果页显示该服务存在**地域可用性限制**；官方 guide 搜索结果还明确提到要确认 API ID，且 Affiliate ID 末尾必须是 990–999；信用展示页面则要求进行指定 credit 标识。对企业工程来说，这意味着 DMM 更像“要按照联盟/API 规则接入”的商业接口，而不是“随便抓就行”的开放数据源。citeturn41view0turn42view0turn52search0turn0search3

R18.dev 的法律与工程画像与 DMM 很不一样。它最大的优势是：**结构化数据许可清晰**，官方直接写明全部结构化数据采用 CC0；这会极大降低你在“元数据字段落库、做分析、做去重规则、做实体解析”上的许可摩擦。但要注意，CC0 明确针对的是**structured data**，并不等于封面、样张、外链图片也自动进入同一许可边界。工程上最稳妥的做法，是把**文本/结构化字段**与**图片资产**分开治理，并在资产表上单独记录许可状态与来源。citeturn8view0turn7search0

JavLibrary、JavDB、JavBus、AVWikiDB 的主要注意点是**无官方数据接口 + 访问控制 + 许可不清**。JavLibrary 需要 session、Cookie、Cloudflare 处理已经被多个项目写进 README 或发布说明；JavDB / JavLibrary 在 Javinizer-Go 中也被直接标记为可配合 FlareSolverr；JavScraper 插件则把“用 jsproxy / 代理访问几个网站下载元数据和图片”写进了项目说明。对于要长期运行的数据平台，这意味着一旦把这些源放入中心化、自动化、大规模任务里，你会同时承担**稳定性风险、封禁风险与 ToS 风险**。citeturn49view0turn19view0turn34search8turn58view0

### 来源使用注意分级

如果从“做内部分析底座”的来源稳定性和使用注意来分，我建议这样看：

**低到中风险**：R18.dev 的结构化字段。原因是许可清晰、dump 明确、适合保留来源与快照版本。citeturn8view0turn9view0

**中风险**：DMM/FANZA API。它是官方渠道，但仍然要遵守 API/联盟/credit 等约束，而且还存在地域限制与潜在使用边界，因此应先做法务/业务规则确认，再决定是否可把返回值持久化、再分发、对外提供。citeturn41view0turn42view0turn52search0turn0search3

**中高到高风险**：任何依赖 Cloudflare、Cookie、代理、Flaresolverr、jsproxy、真人会话的页面抓取源。它们当然可以做“工程验证”或“人工补录工具”，但不适合作为 V1 的核心生产链路。citeturn49view0turn19view0turn34search8turn58view0

## 推荐优先级与版本路线

### 推荐的数据源优先级

从“长期可维护的公开元数据底座”角度，我建议的优先级是：

**第一梯队**：R18.dev、FANZA/DMM API。  
前者解决全量、历史与结构化许可；后者解决官方性、权威字段与相对高质量的目录信息。两者组合足以支撑 V1 的主体实体模型。citeturn8view0turn9view0turn52search0turn53search6

**第二梯队**：Javinizer-Go、MetaTube。  
它们不是源站，但非常适合拿来当接入层、对照实现、回归测试基线，或给内部运营/人工校对团队用的辅助入口。Javinizer-Go 已经具备 CLI/TUI/API/Web UI 与批任务语义；MetaTube 则天然是 provider federation。citeturn19view0turn57view0turn56view0turn55view0

**第三梯队**：JavDB、JavBus。  
两者覆盖面与社区使用度都不错，也有现成 scraper 生态，但更适合做缺失字段补洞，比如补系列、标签、封面、长尾作品。citeturn50search1turn53search7turn59view0

**第四梯队**：JavLibrary、AVWikiDB。  
JavLibrary 的长尾编号、社区标签、评分/评论非常有价值，但它在工程上最不适合无人值守批量采集；AVWikiDB 目前公开证据不足且稳定性判断不一致，建议只放在 observation lane。citeturn49view0turn57view0turn58view0turn36search1turn51search1

### 推荐的 V1 / V2 / V3 接入顺序

**V1**：  
接入 R18.dev dump + DMM/FANZA API，建立 canonical 实体模型与 provenance 体系；同时预留 observation 表，但先不接入高风险 HTML 源。若需要一个现成的内部 UI / 批量测试入口，可并行部署 Javinizer-Go 或 OpenAver 作为“辅助操作台”，但不要把它们当成真源。citeturn8view0turn9view0turn52search0turn19view0turn59view0

**V2**：  
接入 MetaTube federation 与你自写的 JavDB / JavBus 适配器，把这两类来源的字段先写入 observation；只允许通过规则提升把少数字段晋升到 canonical，比如 series、tags、secondary cover、alias title。citeturn55view0turn56view0turn50search1

**V3**：  
引入人工参与的长尾补录模式：JavLibrary 仅支持**精确番号 + 人工确认 + 会话缓存**，AVWikiDB 仅支持**精确 work 页面回填**。这时平台已经有 canonical 底座，不需要让这些高风险源负担全量采集。citeturn58view0turn49view0turn36search1turn51search1

这个顺序的好处是，Codex 在写工程时可以先把**主链路**与**补链路**硬分开：主链路追求稳定、可回放、可审计；补链路追求覆盖面，但默认只产生 observation，不直接改写主字段。citeturn16view0turn55view0turn59view0

## 数据库设计与最终推荐架构

### 对数据库表结构的影响

如果只做“单表 movie_metadata”，后面一定会被多源冲突拖垮。更稳妥的做法是至少拆成以下几层：

`source_registry` 记录来源类型、许可、风险等级、抓取模式；  
`ingest_run` 记录一次 API 拉取、dump 导入或页面抓取任务；  
`raw_payload` 保存原始响应、来源 URL、抓取时间、内容哈希；  
`work_observation` 保存某个 source 对某个作品的一次观察结果；  
`canonical_work` 保存你选出来的主字段；  
`person`、`org`、`series`、`tag` 作为独立维表；  
`work_person_role`、`work_org_role`、`work_tag` 作为关系表；  
`asset` 保存封面、样张、图片许可/缓存状态；  
`field_resolution_log` 保存某字段为何从 observation 提升为 canonical。  

这种设计并不是为了“漂亮”，而是为了适配多源生态的真实形态：Javinizer 强调多源 mix-and-match，MetaTube 明确暴露 provider 优先级，OpenAver 也把来源开关与拖拽排序做成核心功能。你的底座如果不把“字段冲突”设计成一等公民，后面必然返工。citeturn16view0turn55view0turn59view0

### 哪些字段适合作为主字段

建议优先进入 `canonical_work` 的字段是：

`canonical_id`（内部主键）；  
`source_key_preferred`（例如你的“主识别番号”）；  
`title_ja_canonical`；  
`release_date`；  
`runtime_minutes`；  
`maker_id`；  
`label_id`；  
`publisher_id`；  
`series_id`；  
`primary_cover_asset_id`；  
`work_status`；  
`canonical_confidence`。  

理由很简单：这些字段最接近“作品主身份”，同时又最适合由 DMM/R18 这样的稳定源提供。即使有冲突，也通常可以通过优先级、发布日期一致性、编号一致性来裁定。citeturn7search0turn8view0turn52search0turn53search7

### 哪些字段更适合 observation

以下字段更适合保留在 `work_observation` 或“可提升但默认不提升”的层：

各种语言标题与机翻标题；  
社区标签与原始 genre 字符串；  
评分、评论、review 摘要；  
样张 URL 列表；  
男优；  
导演；  
多版本封面与多来源封面；  
CID / 内容 ID / 各站内链 ID；  
女优别名、退役名、跨语言别名；  
站点特有标记，如字幕、4K、UC、LEAK、版本后缀。  

这些字段不是不重要，而是**覆盖不均、定义不统一、争议多**。比如 JavLibrary 的评分/评论很有用，但并不适合作为所有来源的全局唯一事实；AVWikiDB 对男优与 CID 有一定潜力，但证据不足以让它成为一开始就写死的 canonical 字段。citeturn49view0turn57view0turn36search1turn51search1

### 最终推荐架构

我建议的最终架构是一个**双通道、三层数据模型**：

**采集层**分成两条 lane。  
第一条是 **trusted structured lane**：DMM API、R18.dev dump / JSON。  
第二条是 **supplemental observation lane**：MetaTube federation、JavDB、JavBus、JavLibrary、AVWikiDB，以及未来其他 scraper。citeturn8view0turn9view0turn52search0turn55view0turn58view0

**治理层**分成三层。  
最底层是 `raw`，保存原始 payload；  
中间层是 `observation`，把每个来源对每个字段的说法完整保留下来；  
最上层是 `canonical`，只存被规则引擎提升后的主字段。  
规则引擎至少要支持：来源优先级、字段优先级、时间优先级、人工锁定、冲突日志。这个思路与 MetaTube 的 provider priority、OpenAver 的来源排序、Javinizer 的混合字段理念完全同向。citeturn55view0turn59view0turn16view0

**服务层**建议拆成四个服务：  
`ingest-service` 负责 API 拉取、dump 导入、精确番号查询；  
`resolver-service` 负责实体对齐、字段冲突解决与 canonical 提升；  
`asset-service` 负责封面/样张抓取、缓存、许可标记与失效清理；  
`query-service` 对分析任务暴露只读视图。  
如果要交给 Codex 实现，我会建议它先把 `ingest-service` 做成**source adapter interface**，每个来源只需要实现 `search_by_code`、`fetch_detail`、`normalize_observation`、`risk_flags` 四个核心接口，再由统一 scheduler 和 resolver 接管。这个接口形态与 Javinizer-Go、MetaTube、OpenAver 的模块化 scraper 思路高度兼容。citeturn19view0turn55view0turn59view0

落到 V1 的最小可行方案，可以非常明确：  
**用 R18.dev dump 建全量基座，用 DMM/FANZA API 做主字段补全与校正，用 Javinizer-Go 或 OpenAver 做内部测试与回归基线，不把 JavLibrary/JavDB/JavBus/AVWikiDB 放进无人值守主链路。**  
这样做，你会得到一个来源路径更清晰、可追溯性更强、后续也更容易扩展到分析任务的 JAV-MetadataHub。citeturn8view0turn9view0turn52search0turn19view0turn59view0
