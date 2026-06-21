# JavBus Source Spec

This source spec is derived from `docs/research/2026-06-21-public-metadata-sources.md`, `docs/data_sources.md`, and `docs/compliance.md`.

JavBus is not a V1 source. It may only be considered in V2 as a supplemental observation source.

## Source Role

| Attribute | Policy |
| --- | --- |
| Source name | `javbus` |
| Stage | V2 candidate |
| Source type | Community/page-style metadata source |
| Primary use | Missing-field supplement and cross-source comparison |
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
- tags
- cover URL

All observed fields must be written to `source_records` and `field_observations`.

## Required Policy

JavBus may only be considered later for exact-code or narrowly scoped enrichment.

It must not:

- run as a V1 full source
- crawl the whole site
- mirror pages
- directly update canonical fields
- bypass site restrictions

## Risk Notes

The research document treats JavBus as a supplemental source with no confirmed official dump/changefeed and with site-stability and ToS risk.

All uncertain fields remain observations until explicit promotion rules exist.

## Tests

If implemented later, tests must use local fixtures and mocked responses only.

## Prohibited

- No V1 implementation.
- No full crawler.
- No canonical overwrite.
- No video downloading.
- No torrent, magnet, BT, or ed2k collection.
- No piracy resource indexing.
- No Cloudflare, captcha, login, paid-content, or DRM bypass.
- No private personal information collection.
- No facial recognition.
- No real identity inference.
