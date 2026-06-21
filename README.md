# JAV-MetadataHub

JAV-MetadataHub is a public metadata foundation for Japanese adult video metadata analytics.

The project collects, normalizes, governs, and exports public metadata about works, public performer/staff names, companies, series, tags, external IDs, source records, and field observations.

This project is designed for downstream data analysis, not for media downloading or piracy.

## Scope

This project handles public metadata only.

Allowed data:

* Work metadata: code, title, release date, runtime, type, external IDs, external URLs
* Public people metadata: actress, actor, director, public stage names, aliases, source IDs
* Company metadata: maker, label, publisher, studio
* Series metadata
* Tag metadata: genre, keyword, theme
* Source provenance: source, confidence, fetched time, raw JSON/HTML

This project does not support:

* video downloading
* torrent, magnet, BT, or ed2k links
* piracy resource indexing
* DRM bypassing
* paywall bypassing
* captcha bypassing
* account sharing
* private personal information collection
* facial recognition or real identity inference

## Architecture

```text
Public metadata sources
    ↓
Collectors / Importers
    ↓
source_records
    ↓
Parsers
    ↓
field_observations
    ↓
Silver canonical entities
    ↓
Gold analytics exports
    ↓
CSV / Parquet / DuckDB / REST API
```

## Data Source Strategy

V1 focuses on stable structured sources:

1. R18.dev dump as seed / historical dataset
2. FANZA / DMM API as official metadata source

Later versions may add supplemental observation sources:

* Javinizer-Go
* MetaTube
* JavDB
* JavBus
* JavLibrary
* AVWikiDB

Supplemental sources should not directly overwrite canonical fields. They should first enter `source_records` and `field_observations`.

## Core Tables

* `collector_runs`
* `source_records`
* `field_observations`
* `works`
* `work_external_ids`
* `people`
* `person_aliases`
* `person_external_ids`
* `work_people`
* `companies`
* `company_external_ids`
* `work_companies`
* `series`
* `series_external_ids`
* `work_series`
* `tags`
* `work_tags`
* `entity_match_candidates`
* `entity_merge_logs`
* `media_assets`

## Recommended Tech Stack

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

## Quick Start

### 1. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`.

### 4. Start PostgreSQL

```bash
docker compose up -d postgres
```

### 5. Run migrations

```bash
alembic upgrade head
```

### 6. Run tests

```bash
pytest
```

### 7. Run API

```bash
uvicorn jav_metadatahub.api.main:app --reload
```

## Development Commands

```bash
ruff check .
ruff format .
mypy src
pytest
```

## Documentation

* `docs/architecture.md`
* `docs/schema.md`
* `docs/data_sources.md`
* `docs/compliance.md`
* `docs/codex_tasks.md`
* `docs/source_specs/r18_dump.md`
* `docs/source_specs/fanza_dmm_api.md`
* `docs/source_specs/javdb.md`
* `docs/source_specs/javbus.md`
* `docs/source_specs/javlibrary.md`
* `docs/source_specs/avwikidb.md`

## Compliance

This repository must not implement video downloaders, torrent/magnet indexing, piracy features, DRM bypass, paywall bypass, captcha bypass, or private personal information scraping.

All uncertain metadata must remain in `field_observations` until promoted by explicit rules.
