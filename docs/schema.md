# Database Schema

This document is the engineering schema specification for JAV-MetadataHub. It is derived from `README.md`, `AGENTS.md`, and `docs/architecture.md`.

It describes the intended PostgreSQL / SQLAlchemy / Alembic model, but does not implement SQLAlchemy code.

## Data Layers

JAV-MetadataHub uses three data layers.

| Layer | Purpose | Main Objects |
| --- | --- | --- |
| Bronze | Preserve external source evidence with minimal interpretation. | `collector_runs`, `source_records` |
| Silver | Normalize raw source data into governed entities, relationships, external IDs, and field-level observations. | `works`, `people`, `companies`, `series`, `tags`, relationship tables, `field_observations` |
| Gold | Serve analytics-ready exports and read-only API views. | materialized views, CSV, Parquet, DuckDB exports |

All external metadata must flow through:

```text
external source
    -> source_records
    -> parser
    -> field_observations
    -> canonical entity tables
    -> gold exports / API
```

## Core Evidence Tables

### `source_records`

`source_records` is the raw evidence table. It answers:

- Which source produced this record?
- What external key or URL identified it?
- What raw JSON, HTML, SQL-derived row, or text was observed?
- When was it fetched or imported?
- Which collector run and parser version handled it?
- Did the request/import succeed, fail, skip, or return not found?

Rules:

- Save source data here before normalization.
- Preserve failed, skipped, and not-found records when they are part of a collector/import run.
- Do not parse directly into canonical tables without a matching `source_records` row.
- Use `raw_json` for API responses and normalized dump rows; use `raw_html` only for future allowed HTML observation sources.
- Keep `source`, `source_key`, `record_type`, `source_url`, `fetched_at`, `checksum`, and `collector_run_id` when available.

### `field_observations`

`field_observations` is the field evidence table. It answers:

- Which source claimed a field value?
- Which source record supports that value?
- What confidence and observed time are attached?
- Was the observation accepted, rejected, superseded, or still active?
- Which fields conflict across sources?

Rules:

- Save uncertain, conflicting, source-specific, or supplemental values here.
- Do not blindly overwrite canonical fields.
- Every promoted canonical value should be traceable to at least one source record and observation.
- Supplemental sources such as JavDB, JavBus, JavLibrary, and AVWikiDB must write observations first and must not directly update canonical fields.

## Canonical Fields vs Observation Fields

Canonical fields are typed, queryable fields on Silver entity tables. They represent the current best value selected by explicit rules.

Good canonical candidates:

- Work identity: normalized code, preferred title, release date, runtime, work type, censor type.
- Stable relationships: actress/actor/director links, maker/label/publisher/studio links, series links.
- Stable external IDs from V1 sources: FANZA/DMM `content_id`, DMM product IDs, R18.dev `content_id` or `dvd_id`.

Observation fields are source claims that may be incomplete, conflicting, community-specific, translated, or not yet governed.

Observation-first fields:

- Ratings, review counts, comments, community tags.
- Translated titles and source-specific title variants.
- Sample image URL lists and secondary cover URLs.
- Male actor data when source coverage is uneven.
- Alias names, retired names, language-specific names.
- Site-specific flags such as subtitles, 4K, leak labels, limited editions, or version suffixes.

Promotion rule:

- Empty canonical fields may be filled by high-confidence V1 observations.
- Existing canonical fields may only be changed by higher-priority sources or explicit resolution logic.
- Conflicting values remain in `field_observations` until resolved.

## Core Tables

The schema should live under the `javhub` PostgreSQL schema. Use `BIGSERIAL` primary keys unless implementation later chooses an equivalent SQLAlchemy type.

| Table | Layer | Purpose | Primary Key | Foreign Keys | Unique Constraints | Index Recommendations |
| --- | --- | --- | --- | --- | --- | --- |
| `collector_runs` | Bronze | Track each dump import, API collection, backfill, or manual run. | `id` | none | none required | `(source, started_at DESC)` |
| `source_records` | Bronze | Store raw source records and fetch/import status. | `id` | `collector_run_id -> collector_runs.id` | `(source, source_key, record_type)` | `(source, source_key)`, `record_type`, `fetched_at DESC`, GIN on `raw_json` |
| `works` | Silver | Canonical work entity. | `id` | none | no global unique constraint on `code_norm` | `code_norm`, `(code_prefix, code_number)`, `release_date DESC`, trigram indexes on titles |
| `work_external_ids` | Silver | Map works to source-specific identifiers and URLs. | `id` | `work_id -> works.id`, `source_record_id -> source_records.id` | `(source, external_id, id_type)` | `work_id`, `(source, external_id)` |
| `people` | Silver | Public performer, actor, director, and staff entity. | `id` | none | none required in V1 | trigram indexes on `canonical_name`, `name_ja` |
| `person_aliases` | Silver | Public aliases and stage-name variants. | `id` | `person_id -> people.id`, `source_record_id -> source_records.id` | `(person_id, alias, alias_type, source)` | `alias_norm`, trigram on `alias` |
| `person_external_ids` | Silver | Map people to source-specific IDs. | `id` | `person_id -> people.id`, `source_record_id -> source_records.id` | `(source, external_id, id_type)` | `person_id` |
| `work_people` | Silver | Work-person relationship with role and provenance. | `id` | `work_id -> works.id`, `person_id -> people.id`, `source_record_id -> source_records.id` | `(work_id, person_id, role, source)` | `(work_id, role)`, `(person_id, role)` |
| `companies` | Silver | Maker, label, publisher, studio, and related organization entity. | `id` | none | none required in V1 | `name_norm`, trigram on `name` |
| `company_external_ids` | Silver | Map companies to source-specific IDs. | `id` | `company_id -> companies.id`, `source_record_id -> source_records.id` | `(source, external_id, id_type)` | `company_id` |
| `work_companies` | Silver | Work-company relationship with role and provenance. | `id` | `work_id -> works.id`, `company_id -> companies.id`, `source_record_id -> source_records.id` | `(work_id, company_id, role, source)` | `(work_id, role)`, `(company_id, role)` |
| `series` | Silver | Series entity. | `id` | none | none required in V1 | `name_norm`, trigram on `name` |
| `series_external_ids` | Silver | Map series to source-specific IDs. | `id` | `series_id -> series.id`, `source_record_id -> source_records.id` | `(source, external_id, id_type)` | `series_id` |
| `work_series` | Silver | Work-series relationship with provenance. | `id` | `work_id -> works.id`, `series_id -> series.id`, `source_record_id -> source_records.id` | `(work_id, series_id, source)` | `work_id`, `series_id` |
| `tags` | Silver | Source tags, genres, keywords, and future governed tags. | `id` | none | `(name_norm, tag_type, language, source)` | `name_norm`, trigram on `name` |
| `work_tags` | Silver | Work-tag relationship with provenance. | `id` | `work_id -> works.id`, `tag_id -> tags.id`, `source_record_id -> source_records.id` | `(work_id, tag_id, source)` | `work_id`, `tag_id` |
| `field_observations` | Silver | Field-level source claims and conflict evidence. | `id` | `source_record_id -> source_records.id` | none required in V1 | `(entity_type, entity_id)`, `field_name`, `source`, trigram on `field_value_text` |
| `entity_match_candidates` | Silver | Conservative entity match candidates for manual or rule review. | `id` | none generic by design | `(entity_type, left_entity_id, right_entity_id)` | `(entity_type, status)` |
| `entity_merge_logs` | Silver | Audit log for accepted entity merges. | `id` | none generic by design | none required | `(entity_type, from_entity_id, to_entity_id)` |
| `media_assets` | Silver | Image/trailer/profile asset metadata; V1 stores URLs only. | `id` | `work_id -> works.id`, `person_id -> people.id`, `source_record_id -> source_records.id` | `(source, url)` | `work_id`, `person_id` |

## Gold Objects

Gold objects are analytics outputs, not authoritative source evidence.

Recommended Gold views or exports:

- `gold_work_flat`: one row per work with denormalized people, companies, series, and tags.
- `gold_person_profile`: one row per person with public work counts and activity windows.
- `gold_company_monthly_stats`: monthly company production metrics.
- `gold_tag_monthly_trends`: tag trend metrics.
- `gold_actor_cooccurrence`: co-appearance graph export.
- `gold_series_lifecycle`: series timeline and lifecycle metrics.

Gold exports must be reproducible from Bronze and Silver data.

## Entity Resolution Rules

Work auto-match in V1 may use:

- Same source external ID.
- FANZA/DMM `content_id`.
- `code_norm + maker + release_date` when all are available and consistent.

Person auto-match in V1 may use:

- Same source person external ID.

Person names alone must not trigger automatic merges.

Company, series, and tag reuse may use normalized names only with compatible source/type context. Ambiguous cases should create `entity_match_candidates`.

## Media Asset Rules

V1 stores image and media URLs only. It must not download covers, samples, trailers, profile images, or other media files.

`media_assets.download_status` should remain `url_only` in V1.

## Alembic / SQLAlchemy Notes

Future implementation should:

- Use SQLAlchemy 2.x typed declarative models.
- Generate Alembic migrations from this schema spec.
- Create the `javhub` schema and required PostgreSQL extensions such as trigram support if used.
- Preserve constraints, indexes, provenance fields, and confidence fields.
- Avoid adding scraper-specific shortcuts that bypass `source_records` or `field_observations`.
