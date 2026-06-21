# AVWikiDB Source Spec

This source spec is derived from `docs/research/2026-06-21-public-metadata-sources.md`, `docs/data_sources.md`, and `docs/compliance.md`.

AVWikiDB is not a V1 source. It may only be considered in V3 as a supplemental observation source.

## Source Role

| Attribute | Policy |
| --- | --- |
| Source name | `avwikidb` |
| Stage | V3 candidate |
| Source type | Community/wiki-style metadata source |
| Primary use | Actor/director/CID supplement and selected gap filling |
| Canonical authority | None by default |
| Bulk crawling | Not allowed |

## Possible Observation Fields

Future V3 work may observe:

- code or CID candidates
- title variants
- actor/performer supplement
- director supplement
- maker/studio supplement
- series or tag hints when visible
- source URL

All values must be written to `source_records` and `field_observations`.

## Required Policy

AVWikiDB may only be considered for:

- exact-code lookup
- selected missing-field supplement
- manual review workflows
- observation-only ingestion

It must not:

- run in V1
- run as a full-site crawler
- directly overwrite canonical fields
- bypass access controls

## Risk Notes

The research document reports mixed evidence about AVWikiDB coverage and stability. Treat all AVWikiDB fields as uncertain until reviewed.

Actor/director/CID observations may be useful, but they must remain observations unless an explicit resolver promotes them.

## Tests

If implemented later, tests must use local fixtures and mocked responses only.

## Prohibited

- No V1 implementation.
- No full crawler.
- No canonical overwrite.
- No Cloudflare bypass.
- No captcha bypass.
- No login bypass.
- No paid-content bypass.
- No DRM bypass.
- No video downloading.
- No torrent, magnet, BT, or ed2k collection.
- No piracy resource indexing.
- No private personal information collection.
- No facial recognition.
- No real identity inference.
