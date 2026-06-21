# FANZA / DMM API Source Spec

This source spec is derived from `docs/research/2026-06-21-public-metadata-sources.md`, `docs/architecture.md`, `docs/schema.md`, and `docs/compliance.md`.

FANZA / DMM API is a V1 structured source for official public metadata. It must be handled as an API source with credentials, rate limits, retries, logging, fixtures, and mocked tests.

## Source Role

| Attribute | Policy |
| --- | --- |
| Source name | `fanza` |
| Stage | V1 structured API source |
| Source type | Official / affiliate API |
| Primary use | Official metadata, incremental refresh, canonical candidates |
| Canonical authority | Highest default priority for Japanese work metadata and core relationships |
| Bulk access | API pagination with date windows |
| Tests | Mocked HTTP only |

## Configuration

Expected settings:

- `FANZA_BASE_URL`
- `FANZA_API_ID`
- `FANZA_AFFILIATE_ID`
- request timeout
- retry count
- default rate limit

The architecture draft uses this default base URL:

```text
https://api.dmm.com/affiliate/v3
```

Credentials must come from settings or environment variables. They must not be committed or logged.

## API Methods

The V1 client should expose:

- `floor_list`
- `item_list`
- `actress_search`
- `maker_search`
- `genre_search`
- `series_search`

`author_search` may be added later if a concrete metadata need appears.

All requests should include:

- `api_id`
- `affiliate_id`
- `output=json`

## ItemList Parameters

Supported V1 parameters:

| Parameter | Purpose |
| --- | --- |
| `site` | Adult/general site selector; default should support FANZA. |
| `service` | Service/floor filter discovered from FloorList where possible. |
| `floor` | Floor filter discovered from FloorList where possible. |
| `keyword` | Optional search term. |
| `cid` | Exact content ID lookup. |
| `sort` | Default `date` for collection. |
| `hits` | Page size; use a safe default and respect documented/source-researched limits. |
| `offset` | Pagination offset. |
| `gte_date` | Date-window start. |
| `lte_date` | Date-window end. |

## Collection Strategy

Recommended V1 strategy:

```text
FloorList discovery
    -> date-window ItemList scan
    -> paginated raw response storage in source_records
    -> parser
    -> field_observations
    -> canonical promotion through ingestion rules
```

Use date windows instead of unbounded deep pagination. If a date window is too large, split it into smaller windows.

## Source Keys

| API Field | Target | Notes |
| --- | --- | --- |
| `content_id` | `source_records.source_key`, `work_external_ids` | Preferred FANZA source key. |
| `product_id` | `work_external_ids` | Preserve separately. |
| `maker_product` or equivalent product code | `work_external_ids`, `works.code_original` candidate | Most useful human-readable code when present. |
| source URL / affiliate URL | `source_records.source_url`, `work_external_ids.external_url` | Preserve public source/provenance URL. |

If response pages contain multiple items, the implementation may either store page-level `search_result` records and item-level `work` records, or store page-level records first and derive item-level source records during parsing. The chosen policy must be deterministic and tested.

## Field Mapping

| FANZA/DMM Field / Concept | Target | Canonical Candidate | Observation Required |
| --- | --- | --- | --- |
| `content_id` | source key, external ID | yes | yes |
| `product_id` | external ID | yes | yes |
| product code / maker product | code fields, external ID | yes | yes |
| `title` | `works.title_ja` | yes | yes |
| release date / date | `works.release_date` | yes | yes |
| runtime / volume | `works.runtime_minutes` | yes, when safely parsed as minutes | yes |
| actresses | `people`, `work_people` | yes | yes |
| directors | `people`, `work_people` | yes | yes |
| maker | `companies`, `work_companies` | yes | yes |
| label | `companies`, `work_companies` | yes | yes |
| series | `series`, `work_series` | yes | yes |
| genre / keywords | `tags`, `work_tags` | source tag only in V1 | yes |
| image URLs | `media_assets.url` | URL-only candidate | yes |
| review count / rating average | `field_observations` | no | yes |
| sample movie URL | `field_observations` only if retained | no | yes |

## Canonical Promotion Rules

Default priority:

```text
FANZA/DMM API > R18.dev dump > supplemental observations > unknown
```

FANZA/DMM may populate canonical work fields when confidence is high and parsing is deterministic.

FANZA/DMM must still write observations. Canonical fields are current best values, not a replacement for evidence.

## Rate Limit and Retry Policy

The client must include:

- conservative default rate limit
- timeout
- retry with exponential backoff for transient failures
- 429 and 5xx handling
- structured logs
- secret redaction

If repeated failures occur, the collector should mark the `collector_runs` row as failed or partial and stop safely.

## Failure Handling

Save failure context without secrets:

- source
- endpoint
- safe request parameters
- HTTP status
- error class/message
- retry count
- timestamp

Do not log `api_id`, `affiliate_id`, cookies, tokens, or credentials.

## Tests

Tests must use mocked HTTP responses and local fixtures.

Required scenarios:

- auth/query parameters are attached
- pagination uses expected `hits` and `offset`
- date-window parameters are passed
- retry occurs on configured transient failures
- secrets are not logged
- no real external network call is made

## Prohibited

- Do not call real FANZA/DMM API in tests.
- Do not log credentials.
- Do not download images, sample movies, trailers, or videos.
- Do not collect torrent, magnet, BT, or ed2k data.
- Do not bypass paid content, login, captcha, Cloudflare, DRM, or other access controls.
- Do not collect private personal information.
- Do not add facial recognition.
- Do not infer real identities.
