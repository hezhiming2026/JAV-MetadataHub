# AGENTS.md

## 项目

JAV-MetadataHub 是一个面向日本成人成人视频元数据分析的公开元数据底座。


## 技术栈

* Python 3.12+
* PostgreSQL 15+
* SQLAlchemy 2.x
* Alembic
* Pydantic v2
* pydantic-settings
* httpx
* tenacity
* FastAPI
* Typer
* pytest
* ruff
* mypy
* DuckDB / Parquet

## 核心架构

所有外部元数据必须经过以下路径：

```text
external source
    ↓
source_records
    ↓
parser
    ↓
field_observations
    ↓
canonical entity tables
    ↓
gold exports / API
```

## 核心规则

1. 在标准化之前，将原始来源数据保存到 `source_records`。
2. 将不确定或存在冲突的字段保存到 `field_observations`。
3. 不要盲目覆盖 canonical 字段。
4. 为每个字段保留来源、置信度、来源记录 ID 和观测时间。
5. 实体解析必须保持保守。
6. 不得仅根据姓名合并人物。
7. V1 阶段不得爬取第三方 HTML 来源。
8. V1 阶段不得下载图片；只存储 URL。
10. 所有 API client 都必须具备速率限制、重试、日志和测试。
11. 测试中不得调用真实外部 API。
12. 不得记录密钥。
13. 不得提交 `.env`。

## V1 范围

V1 应实现：

* 项目结构
* PostgreSQL schema
* Alembic migrations
* source records
* field observations
* 番号标准化
* R18.dev dump importer
* FANZA / DMM API client
* 基础 parser 和 ingestion flow
* 保守的实体解析
* CSV / Parquet export
* FastAPI 只读 API

V1 不应实现：

* JavDB 全量爬虫
* JavBus 全量爬虫
* JavLibrary 全量爬虫

## 编码规则

* 使用 SQLAlchemy 2.x typed declarative models。
* 使用 Pydantic v2 models 作为 DTO 和 API responses。
* 外部 API client 使用 async `httpx`。
* 使用 `tenacity` 实现重试逻辑。
* parser 应保持确定性，并且易于测试。
* 为 normalizers、parsers、repositories、services 和 API routes 添加测试。
* 测试使用 fixtures 和 mocked responses。
* 不要将业务逻辑放在 route handlers 中。
* 将特定来源的解析逻辑保留在 parser/provider modules 中。

## 测试

适用时运行：

```bash
pytest
ruff check .
ruff format --check .
mypy src
```

如果某个命令无法运行，说明原因，并提供已执行的最接近验证方式。


## 预期任务输出

每个任务都应提供：

1. 变更摘要
2. 修改的文件
3. 运行的测试
4. 已知限制
5. 建议的下一个任务
