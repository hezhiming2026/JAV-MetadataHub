# R18.dev Dump Source Spec

This source spec is derived from `docs/research/2026-06-21-public-metadata-sources.md`, `docs/architecture.md`, `docs/schema.md`, and `docs/compliance.md`.

R18.dev dump is a V1 structured source for seed, backfill, and cross-source validation. It must be handled as public metadata only.

## Source Role

| Attribute | Policy |
| --- | --- |
| Source name | `r18` |
| Stage | V1 structured dump source |
| Source type | Public structured dump |
| Primary use | Historical seed, full snapshot import, English-title supplement, cross-source validation |
| Canonical authority | Secondary to FANZA/DMM for most Japanese canonical fields; preferred for English title when available |
| Bulk access | Dump import only |
| Online JSON/API use | Not required for V1; do not rely on it for bulk ingestion |

## Known Access Pattern

The research document records:

- Latest dump entrypoint: `https://r18.dev/dumps/latest`
- Historical naming pattern: `r18dotdev_dump_YYYY-MM-DD.sql.gz`
- Update pattern: weekly dump publication was observed in the source research.
- File type: gzipped SQL dump.
- License note: structured data was reported as CC0 in the source research.

Implementation must treat these facts as repository-sourced research. Do not refresh them from the internet during tests.

## Import Strategy

Preferred V1 strategy:

```text
download or provide dump file
    -> record collector_run
    -> load into staging database or staging extraction process
    -> serialize relevant source rows into source_records.raw_json
    -> parse source_records
    -> write field_observations
    -> promote only through explicit ingestion rules
```

The importer must not parse directly into canonical tables.

## Source Keys

Use the most stable available key per record type.

| Record Type | Preferred `source_key` | Notes |
| --- | --- | --- |
| `work` | `content_id` when available; otherwise `dvd_id` | Preserve both as external IDs when available. |
| `person` | source person ID when available | Store public names and aliases as observations. |
| `company` | maker/label ID when available | Preserve role such as maker or label. |
| `series` | series ID when available | Preserve source name variants. |
| `tag` | category/tag ID when available | Preserve language and source tag type. |

If a key is missing, generate a deterministic importer key from the source table name and stable row fields. Generated keys must be documented in importer code and tests.

## Field Mapping

| R18 Field / Concept | Target | Canonical Candidate | Observation Required |
| --- | --- | --- | --- |
| `dvd_id` | `works.code_original`, `work_external_ids` | yes, as code candidate | yes |
| `content_id` | `work_external_ids`, `source_records.source_key` | yes, as source identity | yes |
| Japanese title | `works.title_ja` | yes when FANZA/DMM is absent | yes |
| English title | `works.title_en` | yes, preferred when present | yes |
| release date | `works.release_date` | yes | yes |
| runtime minutes | `works.runtime_minutes` | yes, cross-check with FANZA/DMM | yes |
| actresses | `people`, `work_people` | relationship candidate | yes |
| directors | `people`, `work_people` | relationship candidate | yes |
| maker / label | `companies`, `work_companies` | relationship candidate | yes |
| series | `series`, `work_series` | relationship candidate | yes |
| categories / tags | `tags`, `work_tags` | not canonical tag mapping in V1 | yes |
| jacket / gallery URLs | `media_assets.url` | URL-only asset candidate | yes |
| comments/descriptions | `field_observations` | no | yes |

## Canonical Promotion Rules

- R18.dev can fill empty canonical work fields when no higher-priority FANZA/DMM value exists.
- R18.dev should not overwrite populated FANZA/DMM canonical fields without an explicit resolution rule.
- English titles from R18.dev may be preferred when FANZA/DMM does not provide English titles.
- Source tags remain source tags in V1; canonical tag taxonomy is a later task.
- Conflicting release dates, runtimes, names, or relationships must remain visible in `field_observations`.

## Provenance Requirements

Each imported record should preserve:

- source: `r18`
- dump version or dump date when available
- source table or record type
- source key
- source URL when available
- source record ID
- importer version
- checksum when available
- imported/fetched time
- confidence

## Failure Handling

The importer should record failures in `collector_runs` and, where a source record can be identified, in `source_records`.

Expected failure categories:

- dump file missing
- decompression failed
- staging load failed
- schema mismatch
- required key missing
- row parse failed
- relationship target missing

Failures must not discard previously imported source evidence.

## Tests

Tests must use local fixtures only:

- small synthetic SQL-derived records
- serialized source rows
- parser fixtures
- no live dump download
- no live R18.dev calls

## Prohibited

- Do not scrape R18 HTML.
- Do not use R18 online endpoints for V1 bulk import.
- Do not call live R18.dev in tests.
- Do not download images.
- Do not store video URLs, torrent links, magnet links, BT links, ed2k links, or piracy resource links.
- Do not bypass access controls.
- Do not collect private personal information.
- Do not add facial recognition.
- Do not infer real identities.
