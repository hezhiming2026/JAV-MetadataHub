# Codex Tasks

This document is the execution entrypoint for future engineering work. It is derived from `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/schema.md`, `docs/data_sources.md`, and `docs/compliance.md`.

Each task must preserve the project boundary: public metadata only, no video downloading, no torrent/magnet/BT/ed2k, no piracy indexing, no access-control bypass, no private personal data collection, no facial recognition, and no real identity inference.

## Task 1: Initialize Project Structure

**Task goal:** Create the Python project skeleton without implementing business logic.

**Input files:**

- `README.md`
- `AGENTS.md`
- `docs/architecture.md`
- `docs/compliance.md`

**Output files:**

- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `docker-compose.yml`
- `src/jav_metadatahub/__init__.py`
- `tests/`
- optional package placeholder modules needed for import checks

**Requirements:**

- Use Python 3.12+.
- Configure project metadata, dependencies, and dev dependencies.
- Include SQLAlchemy, Alembic, Pydantic v2, pydantic-settings, httpx, tenacity, FastAPI, Typer, pytest, ruff, mypy, DuckDB, and Parquet-related dependencies.
- Add a safe `.env.example` with no secrets.
- Make `python -c "import jav_metadatahub"` work.
- Keep business logic out of this task.

**Prohibited:**

- Do not implement collectors, parsers, importers, API routes, or database models.
- Do not add real credentials.
- Do not call external APIs.

**Acceptance standards:**

- `pip install -e ".[dev]"` or the chosen documented install command can run.
- `python -c "import jav_metadatahub"` succeeds.
- `ruff check .`, `ruff format --check .`, and `pytest` can run against the empty skeleton.

## Task 2: Database Models and Alembic Migration

**Task goal:** Implement the schema from `docs/schema.md` as SQLAlchemy 2.x typed models and an initial Alembic migration.

**Input files:**

- `docs/schema.md`
- `docs/architecture.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/db/base.py`
- `src/jav_metadatahub/db/session.py`
- `src/jav_metadatahub/db/models.py` or focused model modules
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/<initial_revision>.py`
- model/import tests

**Requirements:**

- Create the `javhub` schema.
- Implement all core tables listed in `docs/schema.md`.
- Preserve primary keys, foreign keys, unique constraints, confidence fields, provenance fields, and indexes.
- Use SQLAlchemy 2.x typed declarative models.
- Read `DATABASE_URL` via pydantic-settings.

**Prohibited:**

- Do not add source-specific scraping logic.
- Do not connect to real external APIs.
- Do not model media downloading.

**Acceptance standards:**

- Alembic can create all tables in a test database.
- Model imports pass.
- Schema tests confirm representative constraints and indexes.

## Task 3: Code Normalization Module

**Task goal:** Implement deterministic JAV code normalization.

**Input files:**

- `docs/architecture.md`
- `docs/schema.md`

**Output files:**

- `src/jav_metadatahub/normalizers/code.py`
- `tests/test_normalize_code.py`

**Requirements:**

- Implement `normalize_code(code: str | None)`.
- Return original value, compact normalized value, prefix, and numeric component.
- Handle formats such as `ABP-477`, `abp477`, `ABP_477`, `ABP 477`, `ABP00477`, and `h_123abc001`.
- Keep the function deterministic and side-effect free.

**Prohibited:**

- Do not query external sources.
- Do not infer identity beyond code normalization.

**Acceptance standards:**

- Parameterized tests cover common separators, casing, zero padding, empty input, and complex prefixes.
- Type checking reports no obvious errors.

## Task 4: `source_records` Repository

**Task goal:** Implement repository operations for raw source evidence.

**Input files:**

- `docs/schema.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/repositories/source_records.py`
- repository tests

**Requirements:**

- Support create, get by ID, get by `(source, source_key, record_type)`, and upsert.
- Preserve `raw_json`, `raw_html`, `raw_text`, `http_status`, `fetch_status`, `error_message`, `parser_version`, `checksum`, and `collector_run_id`.
- Make failed and not-found records storable.

**Prohibited:**

- Do not parse source payloads in the repository.
- Do not discard raw evidence.

**Acceptance standards:**

- Repeated upsert updates the same `(source, source_key, record_type)` row.
- Failed records can be stored and retrieved.
- Tests use local fixtures only.

## Task 5: `field_observations` Service

**Task goal:** Implement field-level observation creation and query helpers.

**Input files:**

- `docs/schema.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/services/observations.py`
- observation tests

**Requirements:**

- Create observations for entity type, entity ID, field name, field value, source, source record ID, confidence, and observed time.
- Support querying observations by entity, field, and source.
- Keep `field_value` as structured JSON-compatible data and `field_value_text` for search/debugging.
- Support observation statuses such as active, rejected, and superseded.

**Prohibited:**

- Do not directly overwrite canonical fields.
- Do not promote supplemental source values without explicit resolution logic.

**Acceptance standards:**

- Tests verify observation creation, retrieval, and status handling.
- Conflicting observations can coexist for the same entity field.

## Task 6: R18.dev Dump Importer

**Task goal:** Import R18.dev dump data into `source_records` and observations without relying on live web APIs in tests.

**Input files:**

- `docs/source_specs/r18_dump.md`
- `docs/schema.md`
- `docs/data_sources.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/importers/r18_dump_importer.py`
- `src/jav_metadatahub/parsers/r18_parser.py`
- R18 fixtures and tests

**Requirements:**

- Treat R18.dev as a structured dump source.
- Preserve dump version, import time, source key, and source record ID.
- Store imported records in `source_records` before normalization.
- Map work, people, companies, series, tags, image URLs, and external IDs according to the source spec.
- Write uncertain or conflicting values to `field_observations`.

**Prohibited:**

- Do not scrape R18 HTML.
- Do not call R18 live endpoints in tests.
- Do not download images.

**Acceptance standards:**

- Fixture import creates source records.
- Parsed fields create observations and canonical candidates through ingestion logic.
- Re-import is idempotent for the same source key and record type.

## Task 7: FANZA/DMM API Client

**Task goal:** Implement a safe async client for FANZA/DMM API metadata calls.

**Input files:**

- `docs/source_specs/fanza_dmm_api.md`
- `docs/data_sources.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/collectors/fanza_client.py`
- client tests using mocked HTTP

**Requirements:**

- Use `httpx.AsyncClient`.
- Read base URL, API ID, and affiliate ID from settings.
- Implement FloorList, ItemList, ActressSearch, MakerSearch, GenreSearch, and SeriesSearch methods as specified.
- Attach required auth/query parameters.
- Use tenacity retries, conservative rate limiting, and structured logging.
- Redact secrets in logs.

**Prohibited:**

- Do not call the real API in tests.
- Do not log secrets.
- Do not implement media downloading.

**Acceptance standards:**

- Mocked tests verify request paths, parameters, pagination values, retry behavior, and secret redaction.

## Task 8: FANZA Collector

**Task goal:** Collect FANZA/DMM API responses and store raw payloads in `source_records`.

**Input files:**

- `docs/source_specs/fanza_dmm_api.md`
- `docs/schema.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/collectors/fanza_collector.py`
- collector tests

**Requirements:**

- Use `FanzaClient`.
- Support date-window collection and pagination.
- Create and update `collector_runs`.
- Save each raw page or detail payload before parsing.
- Support dry-run and max-pages controls for tests.

**Prohibited:**

- Do not parse directly into canonical tables.
- Do not call real APIs in tests.
- Do not bypass rate limits.

**Acceptance standards:**

- Mocked multi-page collection stores expected `source_records`.
- Collector run status and counters are updated.
- Dry-run performs no database writes.

## Task 9: Parser + Ingestion Service

**Task goal:** Parse source records into internal DTOs, create observations, and update canonical entities through explicit rules.

**Input files:**

- `docs/schema.md`
- `docs/source_specs/r18_dump.md`
- `docs/source_specs/fanza_dmm_api.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/parsers/base.py`
- `src/jav_metadatahub/parsers/fanza_parser.py`
- `src/jav_metadatahub/parsers/r18_parser.py`
- `src/jav_metadatahub/services/ingestion.py`
- parser and ingestion tests

**Requirements:**

- Parse works, external IDs, people, companies, series, tags, and media URLs.
- Store all source claims as observations.
- Create or reuse canonical entities through repositories/services.
- Preserve source record ID and confidence.
- Store media URLs only.

**Prohibited:**

- Do not blindly overwrite canonical fields.
- Do not download images.
- Do not merge people by name only.

**Acceptance standards:**

- Fixture source records produce expected entities, relationships, and observations.
- Repeated ingestion is idempotent for relationships and external IDs.
- Conflicts remain visible in observations.

## Task 10: Entity Resolution

**Task goal:** Implement conservative V1 entity resolution rules.

**Input files:**

- `docs/schema.md`
- `docs/architecture.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/services/entity_resolution.py`
- entity resolution tests

**Requirements:**

- Match works by same source external ID, FANZA/DMM content ID, or `code_norm + maker + release_date`.
- Match people automatically only by same source person external ID.
- Match companies/series/tags only with compatible source/type context.
- Create `entity_match_candidates` for ambiguous matches.
- Record accepted merges in `entity_merge_logs`.

**Prohibited:**

- Do not merge people only by name.
- Do not auto-merge ambiguous works, aliases, or companies.

**Acceptance standards:**

- Tests prove safe auto-match cases.
- Tests prove ambiguous cases create candidates.
- Tests prove same-name people are not auto-merged.

## Task 11: CSV / Parquet Exporter

**Task goal:** Export Silver and Gold datasets for downstream analytics.

**Input files:**

- `docs/schema.md`
- `docs/architecture.md`

**Output files:**

- `src/jav_metadatahub/exporters/csv_exporter.py`
- `src/jav_metadatahub/exporters/parquet_exporter.py`
- export CLI command
- exporter tests

**Requirements:**

- Export core Silver tables and `gold_work_flat`.
- Support CSV and Parquet.
- Use configured `EXPORT_DIR`.
- Handle empty tables gracefully.

**Prohibited:**

- Do not export raw secrets or credentials.
- Do not export downloaded media.

**Acceptance standards:**

- Tests generate CSV and Parquet in a temporary directory.
- Empty-table exports do not crash.
- Exported columns match documented schema expectations.

## Task 12: FastAPI Read-Only API

**Task goal:** Implement read-only API routes over canonical entities and observations.

**Input files:**

- `docs/schema.md`
- `docs/architecture.md`
- `docs/compliance.md`

**Output files:**

- `src/jav_metadatahub/api/main.py`
- `src/jav_metadatahub/api/dependencies.py`
- `src/jav_metadatahub/api/routes/*.py`
- Pydantic response schemas
- API tests

**Requirements:**

- Implement `GET /health`.
- Implement read-only work, person, company, series, tag, observation, and source routes listed in architecture docs.
- Use Pydantic v2 response models.
- Keep business logic out of route handlers.
- Support pagination where list routes are exposed.

**Prohibited:**

- Do not add write endpoints in V1.
- Do not expose secrets.
- Do not add media download endpoints.

**Acceptance standards:**

- `/health` returns an OK status.
- Route tests pass with a test database.
- API is read-only.

## Task 13: Tests and Docs

**Task goal:** Complete verification coverage and keep documentation aligned with implementation.

**Input files:**

- `README.md`
- `AGENTS.md`
- `docs/*.md`
- source specs
- implemented code and tests

**Output files:**

- Updated README and docs where behavior differs.
- Additional tests for uncovered normalizers, parsers, repositories, services, exporters, and API routes.
- Test fixtures with mocked responses only.

**Requirements:**

- Run `pytest`.
- Run `ruff check .`.
- Run `ruff format --check .`.
- Run `mypy src`.
- Explain any command that cannot run and provide closest verification.
- Keep docs explicit about V1/V2/V3 boundaries.

**Prohibited:**

- Do not add live external API tests.
- Do not commit `.env`.
- Do not weaken compliance boundaries to make tests pass.

**Acceptance standards:**

- Verification commands pass or documented blockers are explicit.
- README links to core docs.
- Source specs remain consistent with implementation.
- Compliance policy remains intact.
