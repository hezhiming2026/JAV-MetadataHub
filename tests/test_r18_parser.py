import hashlib
import json

from jav_metadatahub.parsers.r18_parser import R18DumpParser, stable_compact_json


def observation_values(row: dict[str, object]) -> dict[str, object]:
    parsed = R18DumpParser().parse_work(row)
    return {candidate.field_name: candidate.field_value for candidate in parsed.observations}


def stable_hash(row: dict[str, object]) -> str:
    return hashlib.sha256(stable_compact_json(row).encode("utf-8")).hexdigest()


def test_source_key_prefers_non_empty_content_id_then_dvd_id() -> None:
    parser = R18DumpParser()

    with_content_id = parser.parse_work({"content_id": " cid-001 ", "dvd_id": "ABP-477"})
    with_dvd_id = parser.parse_work({"content_id": "   ", "dvd_id": " IPX-001 "})

    assert with_content_id.source_key == "cid-001"
    assert with_dvd_id.source_key == "IPX-001"


def test_source_key_falls_back_to_row_sha256_for_blank_identity_fields() -> None:
    row = {"content_id": "   ", "dvd_id": "", "title_en": "Hash fallback title"}

    parsed = R18DumpParser().parse_work(row)

    assert parsed.source_key == f"row_sha256:{stable_hash(row)}"
    assert parsed.checksum == stable_hash(row)


def test_checksum_uses_stable_compact_json() -> None:
    row = {"b": "明日花", "a": 1}

    parsed = R18DumpParser().parse_work(row)

    assert stable_compact_json(row) == json.dumps(
        row,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    assert parsed.checksum == hashlib.sha256('{"a":1,"b":"明日花"}'.encode()).hexdigest()


def test_parser_generates_code_observations_from_dvd_id() -> None:
    values = observation_values({"dvd_id": "ABP-00477"})

    assert values["code_original"] == "ABP-00477"
    assert values["code_norm"] == "ABP00477"
    assert values["code_prefix"] == "ABP"
    assert values["code_number"] == "477"


def test_parser_skips_empty_values_and_empty_collections() -> None:
    values = observation_values(
        {
            "content_id": None,
            "dvd_id": "  ",
            "title_ja": "   ",
            "title_en": "",
            "actresses": [None, "", "  "],
            "directors": [],
            "maker": {},
            "tags": [],
            "description": None,
        }
    )

    assert values == {}


def test_release_date_stays_string_and_runtime_requires_safe_int() -> None:
    values = observation_values(
        {
            "release_date": "2020-01-02",
            "runtime_minutes": " 120 ",
            "duration": "121",
        }
    )
    skipped_runtime = observation_values({"runtime_minutes": "120.5", "duration": "not-used"})

    assert values["release_date"] == "2020-01-02"
    assert values["runtime_minutes"] == 120
    assert "runtime_minutes" not in skipped_runtime


def test_media_urls_are_merged_filtered_deduped_and_ordered() -> None:
    values = observation_values(
        {
            "jacket_url": " https://example.test/jacket.jpg ",
            "cover_url": "https://example.test/jacket.jpg",
            "image_url": None,
            "gallery_urls": [
                "https://example.test/1.jpg",
                "",
                "  ",
                42,
                "https://example.test/2.jpg",
            ],
            "sample_images": [
                "https://example.test/1.jpg",
                {"url": "https://example.test/ignored.jpg"},
                "https://example.test/3.jpg",
            ],
        }
    )

    assert values["media_urls"] == [
        "https://example.test/jacket.jpg",
        "https://example.test/1.jpg",
        "https://example.test/2.jpg",
        "https://example.test/3.jpg",
    ]


def test_people_and_tags_arrays_are_filtered_stripped_and_deduped() -> None:
    values = observation_values(
        {
            "actresses": [" Alice ", None, "", "Alice", "Beth"],
            "directors": [" Director A ", "  "],
            "categories": [" Drama ", "Drama", None],
            "tags": [" Tag A ", ""],
        }
    )

    assert values["actresses"] == ["Alice", "Beth"]
    assert values["directors"] == ["Director A"]
    assert values["tags"] == ["Drama", "Tag A"]
