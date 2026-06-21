# JAV-MetadataHub Architecture

> TODO: Paste or generate the full architecture specification here.

This document should describe:
- project positioning
- compliance boundaries
- Bronze / Silver / Gold data layers
- source_records and field_observations
- entity model
- ingestion flow
- parser flow
- export flow
- FastAPI design
- V1 / V2 / V3 roadmap


下面这份是可直接复制进项目文档的 v1.0 方案。资料依据先列在外面：DMM 官方说明其 Web Service 可参照 DMM 商品数据库，使用前需要 DMM 会员、Affiliate 和 API 使用注册；第三方 API v3 汇总也列出 ItemList、ActressSearch、GenreSearch、MakerSearch、SeriesSearch 等常用端点和 `hits`、`offset`、`gte_date/lte_date` 等参数。R18.dev 作者说明已有 database dumps，但同时说明 JSON API 并非真正公共 API，且数据存在已知错误和遗漏。Javinizer / Javinizer-Go 与 MetaTube 可作为多源 provider / metadata server 架构参考，其中 MetaTube 文档也强调尽量以官方数据源为主，第三方源通常会有不准确或缺失。([DMM支持][1])

# JAV-MetadataHub 技术方案 v1.0 + Codex 实施任务书

## 0. 文档版本

```text
项目名称：JAV-MetadataHub
文档版本：v1.0
目标状态：MVP 可落地
核心原则：公开元数据采集、字段血缘、实体治理、可分析、可增量
不包含：视频下载、磁力链接、盗版资源、破解资源、付费绕过、隐私信息采集
```

---

# 1. 项目定位与边界

## 1.1 项目定位

JAV-MetadataHub 是一个面向数据分析的日本 AV 公开元数据底座。它不是下载工具、媒体库整理工具、番号站镜像，也不是单站爬虫。

项目核心目标是：

```text
采集公开元数据
    ↓
保存原始证据
    ↓
标准化作品 / 人物 / 公司 / 系列 / 标签实体
    ↓
保留字段来源、置信度、抓取时间
    ↓
生成可分析数据集
    ↓
对外提供 SQL / Parquet / REST API
```

## 1.2 业务边界

允许处理的数据：

```text
- 作品公开元数据：番号、标题、发行日期、时长、类型、外部 ID、外部 URL
- 公开演职员信息：女优、男优、导演、公开艺名、别名、来源 ID
- 公司公开信息：maker、label、publisher、studio
- 系列公开信息：series
- 标签公开信息：genre、keyword、theme
- 字段来源：source、source_key、source_url、confidence、fetched_at
- 原始公开 JSON / HTML
```

禁止处理的数据：

```text
- 视频文件下载
- 付费视频下载
- 磁力链接
- ed2k 链接
- BT 种子
- 盗版资源索引
- DRM 绕过
- 登录绕过
- 验证码绕过
- 付费墙绕过
- 演员真实身份、住址、私人社媒、私人联系方式
- 非公开个人信息
- 未成年人或疑似非法内容的扩散、索引和推荐
```

## 1.3 项目不是

```text
不是 JavDB 克隆
不是 JavBus 镜像
不是视频下载器
不是媒体中心刮削插件
不是磁力搜索引擎
不是成人内容推荐系统
```

## 1.4 项目是

```text
公开元数据 MDM
公开元数据 DataHub
多源元数据治理系统
后续数据分析项目的数据底座
```

---

# 2. 合规与数据采集原则

## 2.1 合规原则

1. 只采集公开元数据。
2. 不抓取、不保存、不生成盗版资源链接。
3. 不绕过登录、验证码、付费墙、DRM 或访问控制。
4. 遵守 API 条款、robots、速率限制和站点使用约束。
5. 采集器必须可限速、可暂停、可重试、可审计。
6. 对第三方 HTML 页面只做按需补源，不做无差别全站镜像。
7. 图片资源第一版只保存 URL，不下载原图。
8. 人物信息仅限公开艺名和公开演职员信息，不采集私人身份。
9. 所有字段必须有 source、confidence、fetched_at。
10. 不确定字段进入 observation，不直接覆盖主表。

## 2.2 数据治理原则

```text
Raw first：
    原始数据先落 source_records。

Observation first：
    多源字段先进入 field_observations。

Master later：
    主表字段只保存经过规则选择后的当前最佳值。

No blind overwrite：
    补源数据不能无条件覆盖主源字段。

Entity resolution is gradual：
    人物、公司、系列、标签合并要逐步迭代，不要第一版强行合并。

Keep evidence：
    任何主字段都应能追溯到来源记录。
```

---

# 3. 数据源优先级

## 3.1 数据源分层

| 优先级 | 数据源             | 类型              | 用途                   | V1 是否接入 |
| --: | --------------- | --------------- | -------------------- | ------: |
|   1 | FANZA / DMM API | 官方 / 半官方 API    | 主事实源、增量更新            |       是 |
|   2 | R18.dev dump    | 数据 dump / 历史补源  | 历史数据、英文信息、交叉校验       |    V1.5 |
|   3 | Javinizer-Go    | 开源项目            | provider 设计参考、字段映射参考 |      参考 |
|   4 | MetaTube        | metadata server | provider 优先级和服务化参考   |      参考 |
|   5 | JavLibrary      | 页面补源            | 中文/英文标题、演员、评分、标签补充   |      V2 |
|   6 | JavDB           | 页面补源            | 中文标题、标签、评分、社区字段      |      V2 |
|   7 | JavBus          | 页面补源            | 番号详情、演员、厂商、标签补充      |      V2 |
|   8 | AVWikiDB        | 在线数据库           | 素人作品演员、男优、导演补充       |   V2/V3 |

## 3.2 数据源角色

### FANZA / DMM API

角色：

```text
主数据源
主事实源
增量更新源
作品、发行日、时长、maker、label、series、genre 的优先来源
```

适合字段：

```text
- content_id
- product_id
- title_ja
- release_date
- runtime_minutes
- actress
- director
- maker
- label
- series
- genre
- image_url
```

风险：

```text
- 需要 API ID 和 Affiliate ID
- 请求量需要控制
- 成人站点 API 可用性和条款可能变化
- 部分字段覆盖不稳定
```

### R18.dev

角色：

```text
历史 seed 数据
英文标题补源
旧 R18 数据补源
跨源校验源
```

适合字段：

```text
- title_en
- historical work records
- performers
- directors
- makers
- older external IDs
```

风险：

```text
- 不应视为唯一事实源
- 数据存在错误和遗漏
- JSON API 不应强依赖
- dump 格式可能变化
```

### Javinizer-Go

角色：

```text
架构参考
provider 设计参考
多源 scraping 策略参考
NFO 字段映射参考
```

不作为直接数据源。

### MetaTube

角色：

```text
metadata server 架构参考
provider priority 机制参考
API 层参考
```

不作为直接主源。

### JavLibrary / JavDB / JavBus

角色：

```text
按番号补源
缺失字段补全
社区字段参考
```

只在 V2 以后接入。V1 不做全站爬取。

### AVWikiDB

角色：

```text
演员实体补源
素人作品出演者补源
男优 / 导演补源
人工校验参考
```

V2/V3 视可用性接入。

---

# 4. V1 / V2 / V3 分阶段计划

## 4.1 V1：主链路 MVP

目标：

```text
基于 FANZA / DMM API 建立可运行的公开元数据底座。
```

包含：

```text
- Python 项目初始化
- PostgreSQL schema
- Alembic migration
- FANZA / DMM API client
- source_records 原始数据落库
- works / people / companies / series / tags 基础解析
- field_observations 字段观测
- 番号标准化
- 基础实体去重
- CSV / Parquet export
- FastAPI 查询接口
- pytest 测试
```

不包含：

```text
- JavDB / JavBus / JavLibrary 爬虫
- 图片下载
- 复杂人物合并
- 复杂标签 taxonomy
- 图数据库
- 推荐系统
```

## 4.2 V1.5：R18.dev dump 导入

目标：

```text
导入历史数据和英文补源，不破坏 V1 主源结构。
```

包含：

```text
- R18.dev dump importer
- R18 source_records
- work_external_ids 映射
- title_en observation
- people / aliases 补充
- 与 FANZA/DMM 数据交叉校验
```

## 4.3 V2：按需补源和实体治理

目标：

```text
只对缺失字段按番号补源，不做全站爬取。
```

包含：

```text
- JavLibrary provider
- JavDB provider
- JavBus provider
- AVWikiDB provider
- person_external_ids
- company_external_ids
- series_external_ids
- media_assets 只存 URL
- entity_match_candidates
- entity_merge_logs
- tag_mappings
```

## 4.4 V3：分析与服务增强

目标：

```text
形成面向分析项目的稳定 Gold 层。
```

包含：

```text
- gold_work_flat
- gold_person_profile
- gold_company_monthly_stats
- gold_tag_monthly_trends
- gold_actor_cooccurrence
- gold_series_lifecycle
- DuckDB dataset
- Search index
- optional graph export
```

---

# 5. PostgreSQL 表结构设计

## 5.1 Schema 约定

```sql
CREATE SCHEMA IF NOT EXISTS javhub;

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

SET search_path TO javhub;
```

## 5.2 通用字段约定

```text
id：BIGSERIAL 主键
source：数据源，例如 fanza、r18、javlibrary、javdb、javbus、avwikidb
confidence：0.000 - 1.000
created_at：记录创建时间
updated_at：记录更新时间
fetched_at：外部数据抓取时间
observed_at：字段观测时间
```

---

## 5.3 collector_runs

记录每次采集任务。

```sql
CREATE TABLE javhub.collector_runs (
    id BIGSERIAL PRIMARY KEY,

    source TEXT NOT NULL,
    run_type TEXT NOT NULL,              -- full / incremental / backfill / manual
    status TEXT NOT NULL DEFAULT 'running', -- running / success / failed / partial

    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,

    request_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,

    config JSONB,
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_collector_runs_source_started
ON javhub.collector_runs (source, started_at DESC);
```

---

## 5.4 source_records

Bronze 层核心表。保存外部来源原始记录。

```sql
CREATE TABLE javhub.source_records (
    id BIGSERIAL PRIMARY KEY,

    source TEXT NOT NULL,
    source_key TEXT NOT NULL,
    source_url TEXT,

    record_type TEXT NOT NULL,             -- work / person / company / series / tag / search_result / unknown
    payload_type TEXT NOT NULL DEFAULT 'json', -- json / html / text

    raw_json JSONB,
    raw_html TEXT,
    raw_text TEXT,

    http_status INTEGER,
    fetch_status TEXT NOT NULL DEFAULT 'success', -- success / failed / skipped / not_found
    error_message TEXT,

    parser_version TEXT,
    checksum TEXT,

    collector_run_id BIGINT REFERENCES javhub.collector_runs(id),

    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (source, source_key, record_type)
);

CREATE INDEX idx_source_records_source_key
ON javhub.source_records (source, source_key);

CREATE INDEX idx_source_records_record_type
ON javhub.source_records (record_type);

CREATE INDEX idx_source_records_fetched_at
ON javhub.source_records (fetched_at DESC);

CREATE INDEX idx_source_records_raw_json_gin
ON javhub.source_records USING GIN (raw_json);
```

---

## 5.5 works

Silver 层作品主表。

```sql
CREATE TABLE javhub.works (
    id BIGSERIAL PRIMARY KEY,

    code_original TEXT,
    code_norm TEXT,
    code_prefix TEXT,
    code_number TEXT,

    title_ja TEXT,
    title_en TEXT,
    title_zh TEXT,

    release_date DATE,
    runtime_minutes INTEGER,

    censor_type TEXT NOT NULL DEFAULT 'unknown', -- censored / uncensored / unknown
    work_type TEXT NOT NULL DEFAULT 'unknown',   -- normal / vr / amateur / compilation / digital / dvd / unknown

    primary_source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_works_code_norm
ON javhub.works (code_norm);

CREATE INDEX idx_works_code_prefix_number
ON javhub.works (code_prefix, code_number);

CREATE INDEX idx_works_release_date
ON javhub.works (release_date DESC);

CREATE INDEX idx_works_title_ja_trgm
ON javhub.works USING GIN (title_ja gin_trgm_ops);

CREATE INDEX idx_works_title_en_trgm
ON javhub.works USING GIN (title_en gin_trgm_ops);
```

说明：

```text
不要对 code_norm 做全局唯一约束。
原因：
- 同番号可能有 DVD / digital / re-release / compilation 差异
- 不同来源可能把近似编号映射到不同作品
- 唯一性应通过 code_norm + source_external_id + maker + release_date 联合判断
```

---

## 5.6 work_external_ids

作品外部 ID 表。

```sql
CREATE TABLE javhub.work_external_ids (
    id BIGSERIAL PRIMARY KEY,

    work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,

    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    external_url TEXT,
    id_type TEXT NOT NULL,                 -- content_id / product_id / url / database_id / cid / unknown

    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (source, external_id, id_type)
);

CREATE INDEX idx_work_external_ids_work_id
ON javhub.work_external_ids (work_id);

CREATE INDEX idx_work_external_ids_source_external
ON javhub.work_external_ids (source, external_id);
```

---

## 5.7 people

人物主表。女优、男优、导演、作者、其他公开演职员统一进入 people。

```sql
CREATE TABLE javhub.people (
    id BIGSERIAL PRIMARY KEY,

    canonical_name TEXT NOT NULL,
    name_ja TEXT,
    name_en TEXT,
    name_zh TEXT,
    name_kana TEXT,

    person_type TEXT NOT NULL DEFAULT 'unknown', -- performer / director / staff / unknown
    gender_role TEXT NOT NULL DEFAULT 'unknown', -- actress / actor / unknown

    primary_source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),

    is_active BOOLEAN,
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_people_canonical_name_trgm
ON javhub.people USING GIN (canonical_name gin_trgm_ops);

CREATE INDEX idx_people_name_ja_trgm
ON javhub.people USING GIN (name_ja gin_trgm_ops);
```

---

## 5.8 person_aliases

人物别名表。

```sql
CREATE TABLE javhub.person_aliases (
    id BIGSERIAL PRIMARY KEY,

    person_id BIGINT NOT NULL REFERENCES javhub.people(id) ON DELETE CASCADE,

    alias TEXT NOT NULL,
    alias_norm TEXT,
    alias_type TEXT NOT NULL DEFAULT 'unknown', -- ja / en / zh / kana / stage_name / old_name / unknown

    source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (person_id, alias, alias_type, source)
);

CREATE INDEX idx_person_aliases_alias_norm
ON javhub.person_aliases (alias_norm);

CREATE INDEX idx_person_aliases_alias_trgm
ON javhub.person_aliases USING GIN (alias gin_trgm_ops);
```

---

## 5.9 person_external_ids

V1 可建表，V1.5/V2 再大量使用。

```sql
CREATE TABLE javhub.person_external_ids (
    id BIGSERIAL PRIMARY KEY,

    person_id BIGINT NOT NULL REFERENCES javhub.people(id) ON DELETE CASCADE,

    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    external_url TEXT,
    id_type TEXT NOT NULL DEFAULT 'database_id',

    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (source, external_id, id_type)
);

CREATE INDEX idx_person_external_ids_person_id
ON javhub.person_external_ids (person_id);
```

---

## 5.10 work_people

作品—人物关系表。

```sql
CREATE TABLE javhub.work_people (
    id BIGSERIAL PRIMARY KEY,

    work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
    person_id BIGINT NOT NULL REFERENCES javhub.people(id) ON DELETE CASCADE,

    role TEXT NOT NULL,                       -- actress / actor / director / author / staff / unknown
    billing_order INTEGER,

    source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (work_id, person_id, role, source)
);

CREATE INDEX idx_work_people_work_role
ON javhub.work_people (work_id, role);

CREATE INDEX idx_work_people_person_role
ON javhub.work_people (person_id, role);
```

---

## 5.11 companies

公司主表。

```sql
CREATE TABLE javhub.companies (
    id BIGSERIAL PRIMARY KEY,

    name TEXT NOT NULL,
    name_norm TEXT,
    company_type TEXT NOT NULL DEFAULT 'unknown', -- maker / label / publisher / studio / unknown

    primary_source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_companies_name_norm
ON javhub.companies (name_norm);

CREATE INDEX idx_companies_name_trgm
ON javhub.companies USING GIN (name gin_trgm_ops);
```

---

## 5.12 company_external_ids

```sql
CREATE TABLE javhub.company_external_ids (
    id BIGSERIAL PRIMARY KEY,

    company_id BIGINT NOT NULL REFERENCES javhub.companies(id) ON DELETE CASCADE,

    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    external_url TEXT,
    id_type TEXT NOT NULL DEFAULT 'database_id',

    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (source, external_id, id_type)
);

CREATE INDEX idx_company_external_ids_company_id
ON javhub.company_external_ids (company_id);
```

---

## 5.13 work_companies

作品—公司关系表。

```sql
CREATE TABLE javhub.work_companies (
    id BIGSERIAL PRIMARY KEY,

    work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
    company_id BIGINT NOT NULL REFERENCES javhub.companies(id) ON DELETE CASCADE,

    role TEXT NOT NULL,                         -- maker / label / publisher / studio / distributor / unknown

    source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (work_id, company_id, role, source)
);

CREATE INDEX idx_work_companies_work_role
ON javhub.work_companies (work_id, role);

CREATE INDEX idx_work_companies_company_role
ON javhub.work_companies (company_id, role);
```

---

## 5.14 series

系列表。

```sql
CREATE TABLE javhub.series (
    id BIGSERIAL PRIMARY KEY,

    name TEXT NOT NULL,
    name_norm TEXT,

    primary_source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_series_name_norm
ON javhub.series (name_norm);

CREATE INDEX idx_series_name_trgm
ON javhub.series USING GIN (name gin_trgm_ops);
```

---

## 5.15 series_external_ids

```sql
CREATE TABLE javhub.series_external_ids (
    id BIGSERIAL PRIMARY KEY,

    series_id BIGINT NOT NULL REFERENCES javhub.series(id) ON DELETE CASCADE,

    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    external_url TEXT,
    id_type TEXT NOT NULL DEFAULT 'database_id',

    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (source, external_id, id_type)
);

CREATE INDEX idx_series_external_ids_series_id
ON javhub.series_external_ids (series_id);
```

---

## 5.16 work_series

```sql
CREATE TABLE javhub.work_series (
    id BIGSERIAL PRIMARY KEY,

    work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
    series_id BIGINT NOT NULL REFERENCES javhub.series(id) ON DELETE CASCADE,

    source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (work_id, series_id, source)
);

CREATE INDEX idx_work_series_work_id
ON javhub.work_series (work_id);

CREATE INDEX idx_work_series_series_id
ON javhub.work_series (series_id);
```

---

## 5.17 tags

标签表。

```sql
CREATE TABLE javhub.tags (
    id BIGSERIAL PRIMARY KEY,

    name TEXT NOT NULL,
    name_norm TEXT,
    tag_type TEXT NOT NULL DEFAULT 'unknown', -- genre / keyword / theme / format / body / relation / source_raw / unknown
    language TEXT NOT NULL DEFAULT 'unknown',

    source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (name_norm, tag_type, language, source)
);

CREATE INDEX idx_tags_name_norm
ON javhub.tags (name_norm);

CREATE INDEX idx_tags_name_trgm
ON javhub.tags USING GIN (name gin_trgm_ops);
```

---

## 5.18 work_tags

作品—标签关系表。

```sql
CREATE TABLE javhub.work_tags (
    id BIGSERIAL PRIMARY KEY,

    work_id BIGINT NOT NULL REFERENCES javhub.works(id) ON DELETE CASCADE,
    tag_id BIGINT NOT NULL REFERENCES javhub.tags(id) ON DELETE CASCADE,

    source TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (work_id, tag_id, source)
);

CREATE INDEX idx_work_tags_work_id
ON javhub.work_tags (work_id);

CREATE INDEX idx_work_tags_tag_id
ON javhub.work_tags (tag_id);
```

---

## 5.19 field_observations

字段观测表。Silver 层治理核心表。

```sql
CREATE TABLE javhub.field_observations (
    id BIGSERIAL PRIMARY KEY,

    entity_type TEXT NOT NULL,              -- work / person / company / series / tag
    entity_id BIGINT NOT NULL,

    field_name TEXT NOT NULL,
    field_value JSONB,
    field_value_text TEXT,

    source TEXT NOT NULL,
    source_record_id BIGINT REFERENCES javhub.source_records(id),

    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),

    observation_status TEXT NOT NULL DEFAULT 'active', -- active / rejected / superseded
    rejection_reason TEXT,

    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_field_observations_entity
ON javhub.field_observations (entity_type, entity_id);

CREATE INDEX idx_field_observations_field
ON javhub.field_observations (field_name);

CREATE INDEX idx_field_observations_source
ON javhub.field_observations (source);

CREATE INDEX idx_field_observations_value_text_trgm
ON javhub.field_observations USING GIN (field_value_text gin_trgm_ops);
```

说明：

```text
field_value 使用 JSONB，适合保存数字、字符串、数组、结构化对象。
field_value_text 用于搜索和调试。
```

---

## 5.20 entity_match_candidates

V2 表，但建议 V1 先建，后续启用。

```sql
CREATE TABLE javhub.entity_match_candidates (
    id BIGSERIAL PRIMARY KEY,

    entity_type TEXT NOT NULL,              -- work / person / company / series / tag
    left_entity_id BIGINT NOT NULL,
    right_entity_id BIGINT NOT NULL,

    match_score NUMERIC(5,4) NOT NULL CHECK (match_score >= 0 AND match_score <= 1),
    match_reason JSONB,

    status TEXT NOT NULL DEFAULT 'pending', -- pending / accepted / rejected
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (entity_type, left_entity_id, right_entity_id)
);

CREATE INDEX idx_entity_match_candidates_entity_status
ON javhub.entity_match_candidates (entity_type, status);
```

---

## 5.21 entity_merge_logs

V2 表，但建议 V1 先建，后续启用。

```sql
CREATE TABLE javhub.entity_merge_logs (
    id BIGSERIAL PRIMARY KEY,

    entity_type TEXT NOT NULL,
    from_entity_id BIGINT NOT NULL,
    to_entity_id BIGINT NOT NULL,

    merge_reason TEXT,
    merge_confidence NUMERIC(4,3) CHECK (merge_confidence >= 0 AND merge_confidence <= 1),
    merged_by TEXT NOT NULL DEFAULT 'manual', -- manual / rule / model

    merged_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entity_merge_logs_entity
ON javhub.entity_merge_logs (entity_type, from_entity_id, to_entity_id);
```

---

## 5.22 media_assets

V2 表。V1 只存 URL，不下载图片。

```sql
CREATE TABLE javhub.media_assets (
    id BIGSERIAL PRIMARY KEY,

    work_id BIGINT REFERENCES javhub.works(id) ON DELETE CASCADE,
    person_id BIGINT REFERENCES javhub.people(id) ON DELETE CASCADE,

    asset_type TEXT NOT NULL,              -- cover / sample_image / trailer / profile_image
    source TEXT NOT NULL,

    url TEXT NOT NULL,
    local_path TEXT,

    width INTEGER,
    height INTEGER,
    hash TEXT,

    download_status TEXT NOT NULL DEFAULT 'url_only', -- url_only / downloaded / failed / skipped
    copyright_note TEXT,

    source_record_id BIGINT REFERENCES javhub.source_records(id),

    fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (source, url)
);

CREATE INDEX idx_media_assets_work_id
ON javhub.media_assets (work_id);

CREATE INDEX idx_media_assets_person_id
ON javhub.media_assets (person_id);
```

---

# 6. Bronze / Silver / Gold 数据分层

## 6.1 Bronze 层

目标：

```text
原样保存外部数据，不做强清洗。
```

表：

```text
collector_runs
source_records
```

原则：

```text
- API JSON 原样保存到 raw_json
- HTML 原样保存到 raw_html
- 采集失败也记录
- parser_version 必须保存
- source_url 必须保存
- fetched_at 必须保存
```

## 6.2 Silver 层

目标：

```text
将原始数据解析为标准化实体和关系。
```

表：

```text
works
work_external_ids
people
person_aliases
person_external_ids
work_people
companies
company_external_ids
work_companies
series
series_external_ids
work_series
tags
work_tags
field_observations
entity_match_candidates
entity_merge_logs
media_assets
```

原则：

```text
- 主表字段保存当前最佳值
- field_observations 保存所有来源字段
- external_ids 保存来源映射
- 不确定实体先不合并
```

## 6.3 Gold 层

目标：

```text
面向分析项目输出宽表和聚合表。
```

建议物化视图 / 导出表：

```text
gold_work_flat
gold_person_profile
gold_company_monthly_stats
gold_tag_monthly_trends
gold_actor_cooccurrence
gold_series_lifecycle
```

示例：

```sql
CREATE MATERIALIZED VIEW javhub.gold_work_flat AS
SELECT
    w.id AS work_id,
    w.code_original,
    w.code_norm,
    w.title_ja,
    w.title_en,
    w.title_zh,
    w.release_date,
    w.runtime_minutes,
    w.censor_type,
    w.work_type,
    array_remove(array_agg(DISTINCT p.canonical_name) FILTER (WHERE wp.role IN ('actress', 'actor')), NULL) AS performers,
    array_remove(array_agg(DISTINCT c.name) FILTER (WHERE wc.role IN ('maker', 'label', 'publisher', 'studio')), NULL) AS companies,
    array_remove(array_agg(DISTINCT s.name), NULL) AS series,
    array_remove(array_agg(DISTINCT t.name), NULL) AS tags
FROM javhub.works w
LEFT JOIN javhub.work_people wp ON wp.work_id = w.id
LEFT JOIN javhub.people p ON p.id = wp.person_id
LEFT JOIN javhub.work_companies wc ON wc.work_id = w.id
LEFT JOIN javhub.companies c ON c.id = wc.company_id
LEFT JOIN javhub.work_series ws ON ws.work_id = w.id
LEFT JOIN javhub.series s ON s.id = ws.series_id
LEFT JOIN javhub.work_tags wt ON wt.work_id = w.id
LEFT JOIN javhub.tags t ON t.id = wt.tag_id
GROUP BY w.id;
```

---

# 7. source_records 和 field_observations 设计

## 7.1 source_records 的职责

source_records 是证据表，回答：

```text
这个数据来自哪里？
什么时候抓的？
原始 JSON / HTML 是什么？
请求成功了吗？
用哪个 parser 解析的？
```

每条 source_records 对应外部系统的一条原始记录。

示例：

```text
source = fanza
source_key = dmm_content_id
record_type = work
payload_type = json
raw_json = API 原始响应
```

## 7.2 field_observations 的职责

field_observations 是字段证据表，回答：

```text
哪个来源声称这个字段是什么值？
置信度是多少？
该字段是否被主表采用？
不同来源是否冲突？
```

示例：

```text
entity_type = work
entity_id = 10001
field_name = runtime_minutes
field_value = 120
source = fanza
confidence = 0.95
```

另一个来源：

```text
entity_type = work
entity_id = 10001
field_name = runtime_minutes
field_value = 118
source = r18
confidence = 0.75
```

主表 `works.runtime_minutes` 选择 120，但 observation 保留所有证据。

## 7.3 字段采纳规则

V1 默认规则：

```text
FANZA/DMM API > R18.dev > JavLibrary > JavDB > JavBus > AVWikiDB > unknown
```

字段级例外：

```text
title_ja:
    FANZA/DMM 优先

title_en:
    R18.dev 优先

title_zh:
    JavDB / JavLibrary 优先，但 V1 不启用

runtime_minutes:
    FANZA/DMM 优先

actress:
    FANZA/DMM 优先，R18.dev 补充

actor:
    AVWikiDB / JavLibrary 可能更有价值，但 V1 只 observation

director:
    FANZA/DMM 优先，R18.dev 补充

maker:
    FANZA/DMM 优先

label:
    FANZA/DMM 优先

series:
    FANZA/DMM 优先

tags:
    FANZA/DMM genre 先作为 source_raw，后续再 canonical mapping
```

---

# 8. 番号标准化规则

## 8.1 保存字段

works 表保存：

```text
code_original：原始番号
code_norm：标准化番号
code_prefix：前缀
code_number：数字部分
```

## 8.2 标准化函数目标

输入：

```text
ABP-477
abp477
ABP_477
ABP 477
ABP00477
h_123abc001
```

输出：

```text
code_original = 原始输入
code_norm = 移除空格、横线、下划线后的大写值
code_prefix = 尽量解析出的字母/混合前缀
code_number = 尽量解析出的数字部分
```

## 8.3 Python 规则

```python
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedCode:
    original: str | None
    norm: str | None
    prefix: str | None
    number: str | None


def normalize_code(code: str | None) -> NormalizedCode:
    if not code:
        return NormalizedCode(None, None, None, None)

    original = code.strip()
    upper = original.upper()

    # 去除常见分隔符
    compact = re.sub(r"[\s_\-\.]+", "", upper)

    # 常规格式：ABP477 / IPX123 / SSIS001
    m = re.match(r"^([A-Z]+)(\d+)$", compact)
    if m:
        return NormalizedCode(original, compact, m.group(1), m.group(2).lstrip("0") or "0")

    # 复杂格式：H123ABC001
    m = re.match(r"^([A-Z0-9]*?[A-Z]+)(\d+)$", compact)
    if m:
        return NormalizedCode(original, compact, m.group(1), m.group(2).lstrip("0") or "0")

    return NormalizedCode(original, compact, None, None)
```

## 8.4 匹配优先级

作品匹配优先级：

```text
P0：同一 source + external_id 完全一致
P1：FANZA content_id 完全一致
P2：product_id / code_norm 完全一致 + maker 一致
P3：code_norm 一致 + release_date 接近
P4：code_norm 一致 + title 相似 + performer 有交集
P5：标题相似 + performer 有交集 + release_date 接近
```

V1 自动合并只允许 P0-P2。
P3-P5 进入 entity_match_candidates。

---

# 9. 实体去重策略

## 9.1 作品去重

自动合并条件：

```text
- 同 source external_id
- FANZA content_id 一致
- code_norm 一致且 maker 一致且 release_date 完全一致
```

进入候选，不自动合并：

```text
- code_norm 一致但 maker 不一致
- code_norm 一致但 release_date 差距较大
- 标题相似但番号缺失
- 演员重合但番号不同
```

不合并：

```text
- 合集和单品
- DVD 版和 digital 版在 source 上明确区分
- VR 版和普通版
- 同标题不同番号
```

## 9.2 人物去重

自动合并条件 V1：

```text
- 同 source person external_id
```

谨慎候选：

```text
- canonical_name 完全一致 + alias 有交集
- name_ja 完全一致 + 作品交集高
- name_en 完全一致 + source 一致
```

禁止自动合并：

```text
- 只因为中文名相同
- 只因为英文名相同
- 只因为艺名近似
- 只因为出演作品标签相似
```

原因：

```text
人物同名异人风险高，错误合并代价大。
```

## 9.3 公司去重

自动合并条件：

```text
- 同 source company external_id
- name_norm 完全一致 + company_type 一致 + source 一致
```

候选：

```text
- name_norm 高度相似
- maker / label 混用
- 日文名和英文名疑似同一公司
```

不自动合并：

```text
- maker 与 label 不同角色但名字近似
- 子品牌与母公司
- studio 与 publisher
```

## 9.4 系列去重

自动合并条件：

```text
- 同 source series external_id
- name_norm 完全一致 + primary_source 一致
```

候选：

```text
- name 高度相似
- 同 maker 下名称近似
```

不自动合并：

```text
- 不同 maker 下同名系列
```

## 9.5 标签去重

V1 不做 canonical tag 自动合并。

V1 策略：

```text
- 原样保留 source tag
- 记录 language
- 记录 tag_type
- 后续通过 tag_mappings 做 same_as / broader_than / narrower_than
```

---

# 10. Python 项目目录结构

```text
JAV-MetadataHub/
├── README.md
├── AGENTS.md
├── .env.example
├── pyproject.toml
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── docs/
│   ├── architecture.md
│   ├── schema.md
│   ├── data_sources.md
│   ├── compliance.md
│   ├── codex_tasks.md
│   └── api.md
├── src/
│   └── jav_metadatahub/
│       ├── __init__.py
│       ├── config.py
│       ├── logging.py
│       ├── db/
│       │   ├── __init__.py
│       │   ├── session.py
│       │   ├── base.py
│       │   └── models.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── source.py
│       │   ├── work.py
│       │   ├── person.py
│       │   ├── company.py
│       │   ├── series.py
│       │   └── tag.py
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── rate_limit.py
│       │   ├── fanza_client.py
│       │   └── fanza_collector.py
│       ├── importers/
│       │   ├── __init__.py
│       │   └── r18_dump_importer.py
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── fanza_parser.py
│       │   └── r18_parser.py
│       ├── normalizers/
│       │   ├── __init__.py
│       │   ├── code.py
│       │   ├── text.py
│       │   ├── person.py
│       │   └── company.py
│       ├── repositories/
│       │   ├── __init__.py
│       │   ├── source_records.py
│       │   ├── works.py
│       │   ├── people.py
│       │   ├── companies.py
│       │   ├── series.py
│       │   └── tags.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── ingestion.py
│       │   ├── observations.py
│       │   ├── entity_resolution.py
│       │   └── export.py
│       ├── exporters/
│       │   ├── __init__.py
│       │   ├── csv_exporter.py
│       │   └── parquet_exporter.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── dependencies.py
│       │   └── routes/
│       │       ├── works.py
│       │       ├── people.py
│       │       ├── companies.py
│       │       ├── series.py
│       │       ├── tags.py
│       │       └── health.py
│       └── cli.py
├── tests/
│   ├── conftest.py
│   ├── test_normalize_code.py
│   ├── test_fanza_parser.py
│   ├── test_observations.py
│   ├── test_entity_resolution.py
│   └── test_api.py
└── scripts/
    ├── init_db.sh
    ├── run_fanza_backfill.sh
    └── export_gold.sh
```

---

# 11. 推荐技术栈

## 11.1 Runtime

```text
Python 3.12+
PostgreSQL 15+
Docker Compose
```

## 11.2 Python 依赖

```text
SQLAlchemy 2.x
Alembic
Pydantic v2
pydantic-settings
httpx
tenacity
typer
rich
orjson
python-dotenv
FastAPI
uvicorn
pytest
pytest-asyncio
respx
ruff
mypy
duckdb
pyarrow
pandas
```

## 11.3 开发规范

```text
依赖管理：uv 或 poetry
格式化：ruff format
lint：ruff check
类型检查：mypy
测试：pytest
配置：.env + pydantic-settings
数据库 migration：Alembic
```

---

# 12. 采集器设计

## 12.1 Collector 抽象

```python
from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    source: str

    @abstractmethod
    async def fetch(self, **kwargs: Any) -> dict[str, Any] | str:
        pass

    @abstractmethod
    async def collect(self, **kwargs: Any) -> list[int]:
        """
        Return source_record IDs.
        """
        pass
```

## 12.2 FANZA / DMM API Client

职责：

```text
- 构造请求
- 注入 api_id / affiliate_id
- 限速
- 重试
- 错误处理
- 返回 raw JSON
```

建议方法：

```python
class FanzaClient:
    async def floor_list(self) -> dict: ...
    async def item_list(
        self,
        site: str,
        service: str | None = None,
        floor: str | None = None,
        keyword: str | None = None,
        sort: str = "date",
        hits: int = 100,
        offset: int = 1,
        gte_date: str | None = None,
        lte_date: str | None = None,
    ) -> dict: ...

    async def actress_search(self, keyword: str, hits: int = 100, offset: int = 1) -> dict: ...
    async def maker_search(self, keyword: str, hits: int = 100, offset: int = 1) -> dict: ...
    async def genre_search(self, floor_id: str | None = None) -> dict: ...
    async def series_search(self, keyword: str, hits: int = 100, offset: int = 1) -> dict: ...
```

## 12.3 采集策略

V1 推荐按日期分片：

```text
for each floor:
    for each month from start_date to today:
        offset = 1
        while True:
            fetch ItemList(hits=100, offset=offset, gte_date, lte_date)
            save source_records
            parse source_records
            if no more items:
                break
            offset += 100
            sleep(rate_limit)
```

## 12.4 限速策略

```text
默认：1 request / second
错误：指数退避
429 / 5xx：重试
连续失败：暂停 collector_run
所有失败写入 source_records
```

## 12.5 断点续采

依赖 collector_runs + source_records。

V1 简化策略：

```text
- 对每个 source_key 做 upsert
- 已存在 source_key 默认跳过
- 支持 --force-refresh 重新抓取
```

---

# 13. 解析器设计

## 13.1 Parser 抽象

```python
from abc import ABC, abstractmethod


class BaseParser(ABC):
    source: str
    parser_version: str

    @abstractmethod
    def parse_work(self, source_record: dict) -> dict:
        pass
```

## 13.2 FANZA Parser 输出结构

解析输出统一成内部 DTO：

```python
from pydantic import BaseModel, Field
from datetime import date


class ParsedExternalId(BaseModel):
    source: str
    external_id: str
    id_type: str
    external_url: str | None = None
    confidence: float = 0.0


class ParsedPerson(BaseModel):
    name: str
    role: str
    source: str
    external_id: str | None = None
    external_url: str | None = None
    confidence: float = 0.0


class ParsedCompany(BaseModel):
    name: str
    role: str
    source: str
    external_id: str | None = None
    confidence: float = 0.0


class ParsedSeries(BaseModel):
    name: str
    source: str
    external_id: str | None = None
    confidence: float = 0.0


class ParsedTag(BaseModel):
    name: str
    tag_type: str = "genre"
    language: str = "ja"
    source: str
    confidence: float = 0.0


class ParsedWork(BaseModel):
    code_original: str | None = None
    title_ja: str | None = None
    title_en: str | None = None
    title_zh: str | None = None
    release_date: date | None = None
    runtime_minutes: int | None = None
    work_type: str = "unknown"
    censor_type: str = "unknown"

    external_ids: list[ParsedExternalId] = Field(default_factory=list)
    people: list[ParsedPerson] = Field(default_factory=list)
    companies: list[ParsedCompany] = Field(default_factory=list)
    series: list[ParsedSeries] = Field(default_factory=list)
    tags: list[ParsedTag] = Field(default_factory=list)
    media_urls: list[str] = Field(default_factory=list)
```

## 13.3 解析落库流程

```text
source_record
    ↓
parser.parse_work()
    ↓
normalize_code()
    ↓
find_or_create_work()
    ↓
upsert work_external_ids
    ↓
create field_observations
    ↓
find_or_create people / companies / series / tags
    ↓
upsert relationship tables
    ↓
apply master field selection
```

## 13.4 主字段选择

V1 简化规则：

```text
- 空字段可以被高置信度 observation 填充
- 非空字段只有更高优先级来源才能覆盖
- 覆盖前保留旧 observation
- 对冲突明显字段不覆盖，记录 observation
```

---

# 14. 数据导出设计

## 14.1 导出格式

V1 支持：

```text
CSV
Parquet
DuckDB
```

## 14.2 导出目录

```text
exports/
├── csv/
│   ├── works.csv
│   ├── people.csv
│   ├── work_people.csv
│   ├── companies.csv
│   ├── work_companies.csv
│   ├── series.csv
│   ├── work_series.csv
│   ├── tags.csv
│   └── work_tags.csv
├── parquet/
│   ├── works.parquet
│   ├── people.parquet
│   ├── gold_work_flat.parquet
│   └── gold_company_monthly_stats.parquet
└── duckdb/
    └── jav_metadatahub.duckdb
```

## 14.3 Gold 表建议

```text
gold_work_flat：
    一行一个作品

gold_person_profile：
    一行一个人物，包含作品数、活跃期、常见标签、合作公司

gold_company_monthly_stats：
    一行一个公司每月统计

gold_tag_monthly_trends：
    一行一个标签每月趋势

gold_actor_cooccurrence：
    人物共演关系
```

---

# 15. FastAPI 查询接口设计

## 15.1 API 路由

```text
GET /health

GET /works
GET /works/{work_id}
GET /works/by-code/{code}
GET /works/{work_id}/observations
GET /works/{work_id}/sources

GET /people
GET /people/{person_id}
GET /people/{person_id}/works
GET /people/{person_id}/aliases
GET /people/{person_id}/observations

GET /companies
GET /companies/{company_id}
GET /companies/{company_id}/works

GET /series
GET /series/{series_id}
GET /series/{series_id}/works

GET /tags
GET /tags/{tag_id}
GET /tags/{tag_id}/works

GET /analytics/company-monthly
GET /analytics/tag-trends
GET /analytics/person-profile
```

## 15.2 示例查询参数

```text
GET /works?code=ABP-477
GET /works?title=keyword
GET /works?release_date_from=2020-01-01&release_date_to=2020-12-31
GET /works?person_id=123
GET /works?company_id=456
GET /works?tag_id=789
```

## 15.3 响应示例

```json
{
  "id": 10001,
  "code_original": "ABP-477",
  "code_norm": "ABP477",
  "title_ja": "...",
  "title_en": null,
  "release_date": "2016-01-01",
  "runtime_minutes": 120,
  "primary_source": "fanza",
  "confidence": 0.95,
  "external_ids": [
    {
      "source": "fanza",
      "external_id": "...",
      "id_type": "content_id"
    }
  ],
  "people": [
    {
      "id": 20001,
      "name": "...",
      "role": "actress"
    }
  ],
  "companies": [],
  "series": [],
  "tags": []
}
```

---

# 16. 测试策略

## 16.1 单元测试

必须覆盖：

```text
normalize_code
normalize_text
fanza_parser
source_record upsert
field_observation create
entity_resolution basic rules
```

## 16.2 集成测试

必须覆盖：

```text
Alembic migration
DB session
repository CRUD
ingestion service
FastAPI routes
exporter
```

## 16.3 Mock 外部 API

使用：

```text
respx
pytest fixtures
sample raw JSON files
```

目录：

```text
tests/fixtures/fanza/itemlist_page_1.json
tests/fixtures/fanza/item_detail_abp477.json
tests/fixtures/r18/sample_work.json
```

## 16.4 最小验收测试

```bash
pytest
ruff check .
ruff format --check .
mypy src
```

---

# 17. Codex 可执行任务拆解

## Task 01：初始化项目结构

### 任务提示词

```text
请初始化 JAV-MetadataHub Python 项目结构。

要求：
- 使用 Python 3.12+
- 创建 pyproject.toml
- 创建 src/jav_metadatahub 包结构
- 创建 tests 目录
- 创建 docs 目录
- 创建 README.md、AGENTS.md、.env.example
- 添加基础依赖：SQLAlchemy、Alembic、Pydantic v2、pydantic-settings、httpx、tenacity、FastAPI、uvicorn、typer、rich、pytest、ruff、mypy、duckdb、pyarrow
- 添加 ruff、mypy、pytest 基础配置
- 不实现业务逻辑

输出：
- 完整项目目录
- pyproject.toml
- README.md 占位
- AGENTS.md 占位
- .env.example 占位

验收标准：
- python -m pytest 可以运行
- ruff check . 可以运行
- 项目可以被 import：python -c "import jav_metadatahub"
```

---

## Task 02：实现数据库模型和 Alembic migration

### 任务提示词

```text
请实现 JAV-MetadataHub 的 PostgreSQL 数据库模型和 Alembic migration。

输入：
- docs/schema.md 中的表结构设计

要求：
- 使用 SQLAlchemy 2.x Declarative Mapping
- 创建 javhub schema
- 实现以下表：
  - collector_runs
  - source_records
  - works
  - work_external_ids
  - people
  - person_aliases
  - person_external_ids
  - work_people
  - companies
  - company_external_ids
  - work_companies
  - series
  - series_external_ids
  - work_series
  - tags
  - work_tags
  - field_observations
  - entity_match_candidates
  - entity_merge_logs
  - media_assets
- 添加必要索引、唯一约束、外键
- 添加 Alembic 初始 migration
- 创建 db/session.py 和 db/base.py
- 使用 pydantic-settings 从 DATABASE_URL 读取配置

输出：
- SQLAlchemy models
- Alembic migration
- 数据库 session 工具

验收标准：
- alembic upgrade head 可以创建所有表
- pytest 至少包含一个数据库模型 import 测试
- 不连接真实外部 API
```

---

## Task 03：实现番号标准化模块

### 任务提示词

```text
请实现 normalizers/code.py 的番号标准化功能。

要求：
- 实现 normalize_code(code: str | None) -> NormalizedCode
- NormalizedCode 包含 original、norm、prefix、number
- 支持 ABP-477、abp477、ABP_477、ABP 477、ABP00477、h_123abc001 等格式
- 添加 pytest 参数化测试
- 不引入外部服务

输出：
- src/jav_metadatahub/normalizers/code.py
- tests/test_normalize_code.py

验收标准：
- pytest tests/test_normalize_code.py 全部通过
- 类型检查无明显错误
```

---

## Task 04：实现 source_records repository

### 任务提示词

```text
请实现 source_records 的 repository。

要求：
- 文件：repositories/source_records.py
- 支持 create、get_by_id、get_by_source_key、upsert
- upsert 根据 source + source_key + record_type 唯一键
- 支持 raw_json、raw_html、raw_text
- 支持 fetch_status、http_status、error_message、parser_version、checksum
- 添加测试

输出：
- SourceRecordRepository
- 对应 pytest

验收标准：
- 可以创建 source_record
- 相同 source + source_key + record_type 再写入会更新
- 失败记录也可保存
```

---

## Task 05：实现 FANZA / DMM API client

### 任务提示词

```text
请实现 FANZA / DMM API client。

要求：
- 文件：collectors/fanza_client.py
- 使用 httpx.AsyncClient
- 从 settings 读取 FANZA_API_ID、FANZA_AFFILIATE_ID、FANZA_BASE_URL
- 实现 item_list、floor_list、actress_search、maker_search、genre_search、series_search
- 所有请求自动附加 api_id、affiliate_id、output=json
- hits 默认 100
- 支持 offset、gte_date、lte_date、service、floor、keyword、sort
- 使用 tenacity 做重试
- 支持简单限速
- 不在日志中泄露 API key
- 使用 respx 写 mock 测试

输出：
- FanzaClient
- tests/test_fanza_client.py

验收标准：
- mock API 测试通过
- 请求参数正确
- 429/5xx 可重试
- 不访问真实网络
```

---

## Task 06：实现 FANZA collector：抓取并落 source_records

### 任务提示词

```text
请实现 FANZA collector。

要求：
- 文件：collectors/fanza_collector.py
- 使用 FanzaClient
- 支持按日期范围抓取 ItemList
- 支持 hits=100、offset 分页
- 每页原始 JSON 保存到 source_records
- source = fanza
- record_type = search_result 或 work，按实际 payload 设计
- 创建 collector_runs 记录
- 支持 dry_run
- 支持 max_pages 限制，便于测试
- 添加单元测试，不访问真实网络

输出：
- FanzaCollector
- tests/test_fanza_collector.py

验收标准：
- mock 两页数据时可以保存两个 source_records
- collector_runs 状态正确更新
- dry_run 不写数据库
```

---

## Task 07：实现 FANZA parser 和 ingestion service

### 任务提示词

```text
请实现 FANZA parser 和 ingestion service。

要求：
- 文件：parsers/fanza_parser.py
- 文件：services/ingestion.py
- 从 source_records.raw_json 解析 ParsedWork
- 解析字段：
  - code_original
  - title_ja
  - release_date
  - runtime_minutes
  - external_ids
  - actresses
  - directors
  - maker
  - label
  - series
  - genre / tags
  - media_urls 只保存 URL
- 写入 works、work_external_ids、people、person_aliases、work_people、companies、work_companies、series、work_series、tags、work_tags
- 同时写入 field_observations
- 不确定字段进入 observations，不强行覆盖主表
- 添加 fixture 测试

输出：
- FanzaParser
- IngestionService
- tests/test_fanza_parser.py
- tests/test_ingestion.py

验收标准：
- 给定 sample raw_json 可以生成 work
- relationships 正确创建
- observations 正确创建
- 重复 ingestion 不产生重复关系
```

---

## Task 08：实现实体去重基础规则

### 任务提示词

```text
请实现 V1 基础实体去重规则。

要求：
- 文件：services/entity_resolution.py
- 作品：
  - 优先通过 source external_id 查找
  - 其次 code_norm + maker + release_date 匹配
- 人物：
  - 只通过同 source external_id 自动合并
  - 名字相似只进入 entity_match_candidates
- 公司：
  - 同 source external_id 自动合并
  - name_norm + company_type + source 一致可复用
- 系列：
  - 同 source external_id 自动合并
  - name_norm + source 一致可复用
- 标签：
  - name_norm + tag_type + language + source 复用
- 添加测试

输出：
- EntityResolutionService
- tests/test_entity_resolution.py

验收标准：
- 自动合并规则可测试
- 候选匹配会写入 entity_match_candidates
- 不因人物同名直接合并
```

---

## Task 09：实现 CSV / Parquet exporter

### 任务提示词

```text
请实现数据导出模块。

要求：
- 文件：exporters/csv_exporter.py
- 文件：exporters/parquet_exporter.py
- 支持导出：
  - works
  - people
  - work_people
  - companies
  - work_companies
  - series
  - work_series
  - tags
  - work_tags
  - gold_work_flat
- 使用 pandas / pyarrow / duckdb 均可
- 输出到 EXPORT_DIR
- 添加 CLI 命令：javhub export --format csv/parquet
- 添加测试，使用临时目录

输出：
- exporters
- CLI command
- tests/test_exporter.py

验收标准：
- 可以生成 CSV
- 可以生成 Parquet
- 空表时不会崩溃
```

---

## Task 10：实现 FastAPI 基础查询接口

### 任务提示词

```text
请实现 FastAPI 基础查询接口。

要求：
- 文件：api/main.py
- routes：
  - GET /health
  - GET /works
  - GET /works/{work_id}
  - GET /works/by-code/{code}
  - GET /works/{work_id}/observations
  - GET /people/{person_id}
  - GET /people/{person_id}/works
  - GET /companies/{company_id}/works
  - GET /series/{series_id}/works
  - GET /tags/{tag_id}/works
- 使用 Pydantic response schemas
- 支持分页 limit/offset
- 添加测试

输出：
- FastAPI app
- routes
- schemas
- tests/test_api.py

验收标准：
- uvicorn jav_metadatahub.api.main:app 可以启动
- /health 返回 ok
- 查询接口测试通过
```

---

## Task 11：完善 README、AGENTS、docs

### 任务提示词

```text
请完善项目文档。

要求：
- README.md 包含：
  - 项目定位
  - 合规边界
  - 快速开始
  - 环境变量
  - 数据库初始化
  - 运行采集
  - 运行导出
  - 启动 API
- AGENTS.md 包含 Codex 工程约束
- docs/architecture.md 包含架构说明
- docs/schema.md 包含表结构说明
- docs/compliance.md 包含采集边界
- docs/data_sources.md 包含数据源优先级
- 不编写任何视频下载、磁力链接相关内容

输出：
- 完整文档

验收标准：
- 新开发者可按 README 初始化项目
- AGENTS.md 可直接指导 Codex 后续任务
```

---

# 18. AGENTS.md 草案

````markdown
# AGENTS.md

## Project

JAV-MetadataHub is a public metadata foundation for Japanese adult video metadata analytics.

The project only handles public metadata. It must not implement or assist with video downloading, torrent/magnet indexing, piracy, DRM bypassing, paywall bypassing, captcha bypassing, or private personal information collection.

## Tech Stack

- Python 3.12+
- PostgreSQL 15+
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- pydantic-settings
- httpx
- tenacity
- FastAPI
- Typer
- pytest
- ruff
- mypy
- DuckDB / Parquet

## Core Principles

1. Raw data must be saved to `source_records` before normalization.
2. Uncertain fields must be saved to `field_observations`.
3. Do not blindly overwrite master fields.
4. Every field should preserve source, confidence, and fetched/observed time.
5. Entity resolution must be conservative.
6. Do not merge people only by name.
7. Do not crawl entire third-party websites in V1.
8. Do not download images in V1; store URLs only.
9. Do not implement video downloading or magnet/torrent features.
10. All API clients must have rate limiting, retries, logging, and tests.

## Coding Rules

- Use SQLAlchemy 2.x typed declarative models.
- Use Pydantic v2 models for DTOs and API responses.
- Use async httpx for external API clients.
- Use tenacity for retry logic.
- Keep parsers deterministic and testable.
- Add tests for all normalizers, parsers, repositories, and services.
- Do not call real external APIs in tests.
- Use fixtures and mocked responses.
- Do not log secrets.
- Do not commit .env files.

## Testing

Before completing a task, run when applicable:

```bash
pytest
ruff check .
ruff format --check .
mypy src
````

If a command cannot run, explain why and provide the closest verification performed.

## Prohibited Features

Do not add:

* video downloaders
* torrent/magnet collection
* ed2k links
* piracy resource indexing
* DRM bypass
* paywall bypass
* captcha bypass
* account sharing
* private personal data scraping
* facial recognition
* real identity inference

## Expected Task Output

For every task, provide:

1. Summary of changes
2. Files changed
3. Tests run
4. Known limitations
5. Suggested next task

````

---

# 19. README.md 草案

```markdown
# JAV-MetadataHub

JAV-MetadataHub is a public metadata foundation for Japanese adult video metadata analytics.

It collects, normalizes, and serves public metadata such as works, public performer/staff names, companies, series, tags, external IDs, source records, and field observations.

## Scope

This project handles public metadata only.

It does not support:

- video downloading
- torrent or magnet links
- piracy resource indexing
- DRM bypassing
- paywall bypassing
- captcha bypassing
- private personal information collection

## Architecture

```text
External public metadata sources
    ↓
Collectors
    ↓
source_records
    ↓
Parsers
    ↓
field_observations
    ↓
Silver entities
    ↓
Gold analytics tables
    ↓
CSV / Parquet / REST API
````

## V1 Data Source

V1 focuses on FANZA / DMM API as the primary source.

R18.dev dump and other third-party sources may be added in later phases as supplemental sources.

## Main Tables

* collector_runs
* source_records
* works
* work_external_ids
* people
* person_aliases
* person_external_ids
* work_people
* companies
* company_external_ids
* work_companies
* series
* series_external_ids
* work_series
* tags
* work_tags
* field_observations
* entity_match_candidates
* entity_merge_logs
* media_assets

## Quick Start

### 1. Clone

```bash
git clone <repo-url>
cd JAV-MetadataHub
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`.

### 3. Start PostgreSQL

```bash
docker compose up -d postgres
```

### 4. Run migration

```bash
alembic upgrade head
```

### 5. Run tests

```bash
pytest
```

### 6. Run API

```bash
uvicorn jav_metadatahub.api.main:app --reload
```

### 7. Export data

```bash
javhub export --format parquet
```

## Development

```bash
ruff check .
ruff format .
mypy src
pytest
```

## Compliance

See `docs/compliance.md`.

## Data Source Policy

See `docs/data_sources.md`.

````

---

# 20. .env.example 草案

```dotenv
# App
APP_ENV=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+psycopg://javhub:javhub@localhost:5432/javhub

# PostgreSQL Docker
POSTGRES_DB=javhub
POSTGRES_USER=javhub
POSTGRES_PASSWORD=javhub
POSTGRES_PORT=5432

# FANZA / DMM API
FANZA_BASE_URL=https://api.dmm.com/affiliate/v3
FANZA_API_ID=
FANZA_AFFILIATE_ID=

# Collector
COLLECTOR_DEFAULT_RATE_LIMIT_PER_SECOND=1
COLLECTOR_MAX_RETRIES=3
COLLECTOR_TIMEOUT_SECONDS=30

# Export
EXPORT_DIR=./exports

# API
API_HOST=0.0.0.0
API_PORT=8000
````

---

# 21. docker-compose.yml 建议

```yaml
services:
  postgres:
    image: postgres:15
    container_name: jav_metadatahub_postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-javhub}
      POSTGRES_USER: ${POSTGRES_USER:-javhub}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-javhub}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

# 22. pyproject.toml 建议

```toml
[project]
name = "jav-metadatahub"
version = "0.1.0"
description = "Public metadata foundation for JAV metadata analytics"
requires-python = ">=3.12"
dependencies = [
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg[binary]>=3.1",
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "httpx>=0.27",
    "tenacity>=8.2",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "typer>=0.12",
    "rich>=13.7",
    "orjson>=3.10",
    "python-dotenv>=1.0",
    "duckdb>=1.0",
    "pyarrow>=16.0",
    "pandas>=2.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.5",
    "mypy>=1.10",
]

[project.scripts]
javhub = "jav_metadatahub.cli:app"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
strict = false
warn_unused_configs = true
```

---

# 23. V1 最小可交付标准

V1 完成后应具备：

```text
1. 可以启动 PostgreSQL
2. 可以运行 Alembic migration
3. 可以通过 mock 测试 FANZA client
4. 可以保存 source_records
5. 可以解析 sample FANZA raw_json
6. 可以生成 works / people / companies / series / tags
7. 可以生成 field_observations
8. 可以导出 CSV / Parquet
9. 可以启动 FastAPI
10. 可以按番号查询作品
```

V1 不要求：

```text
1. 全量数据完整
2. 演员实体完全合并
3. 标签完全标准化
4. 男优字段完整
5. 导演字段完整
6. 多站点补源完整
7. 图片本地化
8. 搜索体验完善
```

---

# 24. 推荐执行顺序

```text
01 初始化项目结构
02 数据库模型 + Alembic
03 番号标准化
04 source_records repository
05 FANZA client
06 FANZA collector
07 FANZA parser + ingestion
08 entity resolution
09 exporter
10 FastAPI
11 docs 完善
12 接入真实 API 小规模测试
13 导入 R18.dev dump
14 按需补源 provider
```

---

# 25. 最终工程原则

JAV-MetadataHub 的核心不是“抓到更多字段”，而是：

```text
字段可追溯
来源可审计
实体可治理
冲突可解释
增量可持续
分析可复用
```

第一版应该优先保证链路正确，而不是追求字段完美。
所有不确定字段先进入 source_records / field_observations，等数据样本足够后再进入主表或 Gold 层。

[1]: https://support.dmm.com/affiliate/article/44077?utm_source=chatgpt.com "アフィリエイト用に商品データのリストはありませんか？ アフィリエイト DMMヘルプセンター"
