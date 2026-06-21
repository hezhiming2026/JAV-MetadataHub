# Data Sources

This document summarizes the engineering source policy for JAV-MetadataHub. It is derived from `README.md`, `AGENTS.md`, `docs/architecture.md`, and `docs/research/2026-06-21-public-metadata-sources.md`.

It intentionally condenses the Deep Research report instead of copying it.

## Source Strategy

V1 uses stable structured sources only:

1. `R18.dev dump` as the seed and historical structured dataset.
2. `FANZA / DMM API` as the official structured metadata source.

V2/V3 may add supplemental observation sources:

- Javinizer-Go
- MetaTube
- JavDB
- JavBus
- JavLibrary
- AVWikiDB

Supplemental sources must not directly overwrite canonical fields. They must write to `source_records` first and then to `field_observations`.

Third-party HTML sources must not be used as V1 full-site crawlers.

## Version Boundaries

| Stage | Sources | Purpose | Boundary |
| --- | --- | --- | --- |
| V1 | R18.dev dump, FANZA/DMM API | Establish Bronze/Silver/Gold flow and canonical model. | Structured sources only; no third-party HTML crawling. |
| V2 | Javinizer-Go, MetaTube, JavDB, JavBus | Add controlled supplemental observations and compare provider outputs. | Observation-only; exact-code or adapter-based enrichment only. |
| V3 | JavLibrary, AVWikiDB, additional governed sources | Long-tail supplement and manual review workflows. | Observation-only; no bypassing access control or full-site crawling. |

## Source Summary

| Source | Field Coverage | Main Risks | Stage | Engineering Recommendation |
| --- | --- | --- | --- | --- |
| R18.dev dump | Code, titles, release date, runtime, actresses, directors, makers, categories/tags, image URLs. | Dump schema may change; online JSON API should not be treated as the main bulk interface; image licensing is separate from structured data. | V1 | Use dump import as repeatable seed/backfill. Store each imported record in `source_records`; write uncertain fields to `field_observations`. |
| FANZA / DMM API | Code/product IDs, titles, release date, runtime, actresses, directors, maker, label, series, genres, image URLs. | Requires API credentials; affiliate/credit rules; regional availability; unknown rate limits. | V1 | Use as official structured API source with conservative rate limits, retries, logs, and mocked tests. |
| Javinizer-Go | Aggregated provider fields such as title, cast, studio, series, tags, image URLs, and NFO-style mappings. | It is an aggregation/tooling layer, not a canonical upstream; may rely on sources with anti-crawl controls. | V2 | Use as reference implementation, compatibility baseline, or optional internal adapter. Do not treat as authoritative truth. |
| MetaTube | Provider-federated metadata such as title, actors, director, studio, genres, and image URLs depending on provider. | Provider quality varies; not an authoritative source; depends on configured upstreams. | V2 | Use as federation/reference layer only. Preserve provider identity in observations. |
| JavDB | Code, title, release date, runtime, actresses, director, maker/studio, series, tags, cover URLs, possible ratings. | No confirmed official dump/API; HTML/source stability and anti-crawl risk; Cloudflare/proxy-related ecosystem signals. | V2 | Supplemental observation source only. No V1 full crawler; no bypass; no canonical overwrite. |
| JavBus | Code, title, release date, runtime, actresses, director, maker/studio, series, tags, cover URLs. | No confirmed official dump/API; page stability and ToS risk; proxy/site availability risk. | V2 | Supplemental observation source only. Exact-code enrichment only if later approved. |
| JavLibrary | Code, title, actresses, director, maker, label, tags, rating/review-like fields. | High anti-crawl/session/Cloudflare risk; no public bulk interface; rating/review data is community-specific. | V3 | Long-tail/manual observation source only. No full-site crawler and no access-control bypass. |
| AVWikiDB | Code/CID candidates, actor/director supplement, possibly person and work details. | Evidence is less complete and stability is uncertain; possible access-control changes. | V3 | Observation-only supplement for selected gaps; no canonical overwrite. |

## Canonical Source Priority

Default field promotion priority:

```text
FANZA/DMM API > R18.dev dump > supplemental observations > unknown
```

Supplemental observations include JavDB, JavBus, JavLibrary, AVWikiDB, MetaTube, and Javinizer-Go output. They may help detect conflicts or missing values but cannot directly write canonical fields.

Field-level notes:

- `title_ja`: FANZA/DMM preferred when available.
- `title_en`: R18.dev preferred when available.
- `title_zh`: observation-only until a governed translation policy exists.
- `runtime_minutes`: FANZA/DMM preferred; R18.dev can cross-check.
- `actress`: FANZA/DMM preferred; R18.dev can supplement.
- `actor`: observation-only in V1 because coverage varies.
- `director`: FANZA/DMM preferred; R18.dev can supplement.
- `maker`, `label`, `series`: FANZA/DMM preferred when available.
- `tags`: preserve source tags first; canonical tag mapping is a later governance task.
- ratings, comments, review counts, community heat, and ranking signals: observation-only.

## V1 Structured Sources

### R18.dev Dump

Role:

- Cold-start seed.
- Historical backfill.
- Cross-source validation.
- English-title and legacy-data supplement where present.

Engineering policy:

- Prefer dump import over online JSON calls for bulk data.
- Store imported work/person/company/series/tag records as `source_records`.
- Preserve dump version, observed time, checksum when available, and importer version.
- Convert source-specific fields into `field_observations` before promotion.

### FANZA / DMM API

Role:

- Official structured metadata source.
- Incremental refresh source.
- High-confidence candidate for work identity and core relationships.

Engineering policy:

- Use async `httpx`, retries, rate limiting, structured logging, and tests with mocked responses.
- Never call real external APIs in tests.
- Never log API credentials or affiliate IDs as secrets.
- Store every raw response page or detail response in `source_records`.
- Use parser/ingestion flow to create observations and canonical candidates.

## V2/V3 Supplemental Sources

Supplemental sources exist to improve coverage and identify conflicts. They are not canonical sources.

Allowed future pattern:

```text
exact code or approved adapter input
    -> source_records
    -> parser/provider module
    -> field_observations
    -> candidate review / explicit promotion rule
```

Disallowed pattern:

```text
third-party HTML source
    -> direct canonical update
```

## Third-Party HTML Policy

JavDB, JavBus, JavLibrary, and AVWikiDB must not be V1 full crawler sources.

Future use must follow all of these constraints:

- Exact-code lookup or small, targeted supplement only.
- No full-site mirroring.
- No Cloudflare bypass.
- No captcha bypass.
- No login bypass.
- No paid-content bypass.
- No DRM bypass.
- No proxy or solver integration whose purpose is to bypass access controls.
- No private personal information collection.
- No facial recognition.
- No real identity inference.
- All data goes through `source_records` and `field_observations`.
- No direct canonical overwrite.

## Image Policy

V1 stores image URLs only. It must not download covers, sample images, trailers, or profile images.

Image URL observations should preserve:

- source
- source record ID
- observed time
- asset type
- source URL
- license/copyright note when known

## Testing Policy

All source clients and importers must be tested with fixtures and mocked responses. Tests must not call real external APIs or websites.
