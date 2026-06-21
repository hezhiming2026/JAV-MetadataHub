# JavDB Source Spec

This source spec is derived from `docs/research/2026-06-21-public-metadata-sources.md`, `docs/data_sources.md`, and `docs/compliance.md`.

JavDB is not a V1 source. It may only be considered in V2 as a supplemental observation source.

## Source Role

| Attribute | Policy |
| --- | --- |
| Source name | `javdb` |
| Stage | V2 candidate |
| Source type | Community/page-style metadata source |
| Primary use | Missing-field supplement and conflict observation |
| Canonical authority | None by default |
| Bulk crawling | Not allowed |

## Possible Observation Fields

Future V2 work may observe:

- code/title variants
- release date
- runtime
- actresses
- director
- maker/studio
- series
- tags/community categories
- cover URL
- rating-like signals when available

All observed fields must be written to `source_records` and `field_observations`.

## Required Policy

Allowed future pattern:

```text
approved exact code
    -> source_records
    -> parser/provider
    -> field_observations
    -> candidate review
```

JavDB must not directly update:

- `works`
- `people`
- `companies`
- `series`
- `tags`
- relationship tables

Canonical promotion requires explicit field-level resolution logic.

## Risk Notes

The research document describes JavDB as a source with no confirmed official public dump/API and with anti-crawl/access-stability risk in the surrounding ecosystem.

This project must not implement:

- full-site crawling
- Cloudflare bypass
- captcha bypass
- login bypass
- paid-content bypass
- proxy/solver integration for access-control bypass

## Tests

If implemented later, tests must use local fixtures and mocked responses only.

## Prohibited

- No V1 implementation.
- No full crawler.
- No canonical overwrite.
- No video downloading.
- No torrent, magnet, BT, or ed2k collection.
- No piracy resource indexing.
- No access-control bypass.
- No private personal information collection.
- No facial recognition.
- No real identity inference.
