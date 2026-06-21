# AGENTS.md

## Project

JAV-MetadataHub is a public metadata foundation for Japanese adult video metadata analytics.

The project only handles public metadata. It must not implement or assist with video downloading, torrent/magnet indexing, piracy, DRM bypassing, paywall bypassing, captcha bypassing, account sharing, or private personal information collection.

## Tech Stack

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

## Core Architecture

All external metadata must flow through this path:

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

## Core Rules

1. Save raw source data to `source_records` before normalization.
2. Save uncertain or conflicting fields to `field_observations`.
3. Do not blindly overwrite canonical fields.
4. Preserve source, confidence, source record ID, and observed time for every field.
5. Entity resolution must be conservative.
6. Do not merge people only by name.
7. Do not crawl third-party HTML sources in V1.
8. Do not download images in V1; store URLs only.
9. Do not implement video downloading or magnet/torrent features.
10. All API clients must have rate limiting, retries, logging, and tests.
11. Do not call real external APIs in tests.
12. Do not log secrets.
13. Do not commit `.env`.

## V1 Scope

V1 should implement:

* project structure
* PostgreSQL schema
* Alembic migrations
* source records
* field observations
* code normalization
* R18.dev dump importer
* FANZA / DMM API client
* basic parser and ingestion flow
* conservative entity resolution
* CSV / Parquet export
* FastAPI read-only API

V1 should not implement:

* JavDB full crawler
* JavBus full crawler
* JavLibrary full crawler
* Cloudflare bypass
* captcha bypass
* paywall bypass
* image downloading
* video downloading
* torrent/magnet/ed2k support

## Coding Rules

* Use SQLAlchemy 2.x typed declarative models.
* Use Pydantic v2 models for DTOs and API responses.
* Use async `httpx` for external API clients.
* Use `tenacity` for retry logic.
* Keep parsers deterministic and testable.
* Add tests for normalizers, parsers, repositories, services, and API routes.
* Use fixtures and mocked responses for tests.
* Keep business logic out of route handlers.
* Keep source-specific parsing inside parser/provider modules.

## Testing

Run when applicable:

```bash
pytest
ruff check .
ruff format --check .
mypy src
```

If a command cannot run, explain why and provide the closest verification performed.

## Prohibited Features

Do not add:

* video downloaders
* torrent, magnet, BT, or ed2k collection
* piracy resource indexing
* DRM bypass
* paywall bypass
* captcha bypass
* account sharing
* private personal data scraping
* facial recognition
* real identity inference
* scraping of non-public personal information

## Expected Task Output

For every task, provide:

1. Summary of changes
2. Files changed
3. Tests run
4. Known limitations
5. Suggested next task
