# JavLibrary Source Spec

This source spec is derived from `docs/research/2026-06-21-public-metadata-sources.md`, `docs/data_sources.md`, and `docs/compliance.md`.

JavLibrary is not a V1 source. It may only be considered in V3, or a late V2 manual workflow, as a supplemental observation source.

## Source Role

| Attribute | Policy |
| --- | --- |
| Source name | `javlibrary` |
| Stage | V3 candidate; late V2 only if explicitly approved |
| Source type | Community/page-style metadata source |
| Primary use | Long-tail supplement, tags, rating/review-like observations |
| Canonical authority | None by default |
| Bulk crawling | Not allowed |

## Possible Observation Fields

Future work may observe:

- code/title variants
- public actress names
- director
- maker
- label
- series when visible
- tags/community categories
- rating-like values
- review/comment metadata when allowed and public

These fields are observation-only until explicit resolution rules exist.

## Required Policy

JavLibrary may only be considered for:

- exact-code lookup
- manual review
- small controlled supplement
- observation-only ingestion

It must not directly update canonical fields.

## Risk Notes

The research document flags JavLibrary as high risk because surrounding public tooling reports session, cookie, anti-bot, and Cloudflare-related constraints.

This project must not implement bypass tactics. If public access requires a challenge, login, paid access, or human session, automated collection must stop.

## Rating and Review Caveats

Ratings, reviews, comment counts, and community sentiment are not canonical work facts.

They must be stored as observations or future metric snapshots with:

- source
- observed time
- source record ID
- confidence
- raw value

They must not overwrite canonical work fields.

## Tests

If implemented later, tests must use local fixtures and mocked responses only.

## Prohibited

- No V1 implementation.
- No full-site crawling.
- No Cloudflare bypass.
- No captcha bypass.
- No login/session bypass.
- No paid-content bypass.
- No DRM bypass.
- No canonical overwrite.
- No video downloading.
- No torrent, magnet, BT, or ed2k collection.
- No piracy resource indexing.
- No private personal information collection.
- No facial recognition.
- No real identity inference.
