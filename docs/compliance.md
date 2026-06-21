# Compliance Policy

This document defines the compliance boundary for JAV-MetadataHub. It is derived from `README.md`, `AGENTS.md`, `docs/architecture.md`, and `docs/research/2026-06-21-public-metadata-sources.md`.

The project handles public metadata only. It must not become a downloader, piracy index, access-control bypass tool, identity inference system, or private personal data collector.

## Allowed Data

JAV-MetadataHub may collect and process public metadata such as:

- Work metadata: code, normalized code, title, release date, runtime, type, external IDs, public external URLs.
- Public people metadata: actress, actor, director, staff role, public stage names, public aliases, source IDs.
- Company metadata: maker, label, publisher, studio, distributor, source IDs.
- Series metadata.
- Tag metadata: genre, keyword, theme, source tag names.
- Public source provenance: source name, source key, source URL, confidence, fetched/imported time, source record ID.
- Raw public JSON, SQL-dump-derived rows, and future approved public HTML records when allowed by source policy.

## Prohibited Data and Features

Do not add, document as an implementation target, or assist with:

- Video downloading.
- Paid video downloading.
- Torrent, magnet, BT, or ed2k collection.
- Piracy resource indexing.
- DRM bypass.
- Paywall bypass.
- Captcha bypass.
- Cloudflare bypass.
- Login bypass.
- Account sharing.
- Private personal data scraping.
- Facial recognition.
- Real identity inference.
- Scraping of non-public personal information.
- Private contact information, addresses, private social accounts, or real-life identity data.
- Any workflow intended to obtain, distribute, or locate unauthorized media files.

## Required Data Flow

All external metadata must flow through the governed path:

```text
external source
    -> source_records
    -> parser
    -> field_observations
    -> canonical entity tables
    -> gold exports / read-only API
```

Compliance rules:

- Raw source evidence must be saved before normalization.
- Uncertain or conflicting fields must be saved as observations.
- Supplemental sources must not directly overwrite canonical fields.
- Every promoted field should preserve source, confidence, source record ID, and observed time.
- Entity resolution must be conservative.
- People must not be merged only by name.

## Source Access Policy

### V1 Sources

V1 may use:

- R18.dev dump as a structured dump source.
- FANZA/DMM API as an official structured API source.

V1 must not use:

- JavDB full crawler.
- JavBus full crawler.
- JavLibrary full crawler.
- AVWikiDB full crawler.
- Any third-party HTML full-site crawler.

### V2/V3 Supplemental Sources

JavDB, JavBus, JavLibrary, and AVWikiDB may only be considered later as supplemental observation sources.

Future use must be limited to approved, narrow workflows:

- Exact-code lookup.
- Manual or small-batch field supplement.
- Observation-only ingestion.
- Explicit review before any field promotion.

Future use must not include:

- Full-site crawling.
- Mirroring.
- Anti-bot bypass.
- Cloudflare bypass.
- Captcha solving.
- Login/session bypass.
- Paid-content access.
- DRM circumvention.

## API and Dump Usage Principles

API clients and dump importers must:

- Respect source terms, robots policies, documented rate limits, and access restrictions.
- Use conservative rate limits and retry policies.
- Log requests and failures without logging secrets.
- Save raw responses or imported records to `source_records`.
- Preserve provenance and confidence.
- Be testable with fixtures and mocked responses.
- Avoid real network calls in tests.

Secrets policy:

- Do not commit `.env`.
- Do not log API IDs, affiliate IDs, tokens, cookies, or credentials.
- Do not include real credentials in fixtures.

## Image Policy

V1 stores image URLs only.

Do not download:

- Cover images.
- Sample images.
- Profile images.
- Trailers.
- Any other media assets.

Image-related metadata may be stored as URL observations with source, source record ID, asset type, and observed time.

## Privacy Policy

Allowed people data is limited to public performance metadata:

- Public stage names.
- Public aliases.
- Public source IDs.
- Public role labels such as actress, actor, director, or staff.

Disallowed people data:

- Real identity inference.
- Face matching.
- Facial recognition.
- Private names.
- Private addresses.
- Private contact information.
- Private social accounts.
- Non-public personal information.

## Tests and Fixtures

Tests must not call real external APIs or websites.

Use:

- Static fixtures.
- Mocked HTTP responses.
- Local sample dump rows.
- Synthetic records.

Do not use:

- Real credentials.
- Live API calls.
- Browser automation against third-party adult sites.
- Captcha, Cloudflare, login, or paywall bypass tools.
