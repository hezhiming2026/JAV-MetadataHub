import json
from pathlib import Path

from jav_metadatahub.parsers.fanza_parser import FanzaParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "fanza"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def observation_values(item: dict[str, object]) -> dict[str, object]:
    parsed = FanzaParser().parse_work(item)
    return {candidate.field_name: candidate.field_value for candidate in parsed.observations}


def test_parse_work_maps_common_fanza_item_shape() -> None:
    item = load_fixture("item_work.json")

    parsed = FanzaParser().parse_work(item)
    values = {candidate.field_name: candidate.field_value for candidate in parsed.observations}

    assert parsed.source_key == "cid-001"
    assert parsed.source_url == "https://www.dmm.co.jp/digital/videoa/-/detail/=/cid=cid-001/"
    assert values["content_id"] == "cid-001"
    assert values["product_id"] == "product-001"
    assert values["dvd_id"] == "DVD-001"
    assert values["code_original"] == "ABP-00477"
    assert values["code_norm"] == "ABP00477"
    assert values["code_prefix"] == "ABP"
    assert values["code_number"] == "477"
    assert values["title_ja"] == "サンプル作品"
    assert values["release_date"] == "2020-01-02"
    assert values["runtime_minutes"] == 120
    assert values["actresses"] == ["Alice", "Beth"]
    assert values["actors"] == ["Bob", "Carl"]
    assert values["directors"] == ["Director A"]
    assert values["maker"] == "Maker One"
    assert values["label"] == "Label One"
    assert values["series"] == "Series One"
    assert values["tags"] == ["Drama", "Featured"]
    assert values["source_url"] == "https://www.dmm.co.jp/digital/videoa/-/detail/=/cid=cid-001/"
    assert "affiliate.example.invalid" not in str(values)


def test_iteminfo_helpers_support_string_dict_and_lists() -> None:
    values = observation_values(
        {
            "actresses": [" Alice ", "Alice", {"name": " Beth "}, "", None],
            "actor": {"name": " Actor One "},
            "iteminfo": {
                "director": " Director One ",
                "maker": [{"name": " Maker One "}, "Maker Two"],
                "label": " Label One ",
                "series": {"name": " Series One "},
                "genre": [" Drama ", {"name": " Featured "}],
            },
        }
    )

    assert values["actresses"] == ["Alice", "Beth"]
    assert values["actors"] == ["Actor One"]
    assert values["directors"] == ["Director One"]
    assert values["maker"] == "Maker One"
    assert values["label"] == "Label One"
    assert values["series"] == "Series One"
    assert values["tags"] == ["Drama", "Featured"]


def test_source_url_observation_ignores_affiliate_url() -> None:
    values = observation_values(
        {
            "content_id": "cid-001",
            "affiliateURL": "https://affiliate.example.invalid/secret",
            "affiliate_url": "https://affiliate.example.invalid/secret-2",
        }
    )

    assert "source_url" not in values
    assert "affiliate.example.invalid" not in str(values)


def test_release_date_stays_string_and_runtime_requires_safe_int() -> None:
    values = observation_values({"date": "2020-01-02", "volume": " 120 "})
    skipped_runtime = observation_values({"date": "2020-01-02", "volume": "120.5"})

    assert values["release_date"] == "2020-01-02"
    assert values["runtime_minutes"] == 120
    assert skipped_runtime["release_date"] == "2020-01-02"
    assert "runtime_minutes" not in skipped_runtime


def test_empty_values_are_not_emitted() -> None:
    values = observation_values(
        {
            "content_id": "  ",
            "product_id": "",
            "dvd_id": None,
            "title": "   ",
            "date": "",
            "volume": "not-a-number",
            "actresses": [None, "", "   "],
            "iteminfo": {
                "director": [],
                "maker": [{"name": " "}],
                "label": {},
                "series": [],
                "genre": [],
            },
            "imageURL": {"large": " "},
            "sampleImageURL": {"sample_s": {"image": []}},
        }
    )

    assert values == {}


def test_media_urls_are_merged_filtered_deduped_and_ordered() -> None:
    values = observation_values(
        {
            "imageURL": {
                "large": " https://pics.example.invalid/large.jpg ",
                "small": "https://pics.example.invalid/small.jpg",
            },
            "sampleImageURL": {
                "sample_s": {
                    "image": [
                        "https://pics.example.invalid/sample-1.jpg",
                        "",
                        "https://pics.example.invalid/sample-2.jpg",
                    ]
                },
                "sample_l": {
                    "image": [
                        "https://pics.example.invalid/sample-1.jpg",
                        {"url": "https://pics.example.invalid/sample-3.jpg"},
                    ]
                },
            },
            "image_url": "https://pics.example.invalid/large.jpg",
        }
    )

    assert values["media_urls"] == [
        "https://pics.example.invalid/large.jpg",
        "https://pics.example.invalid/small.jpg",
        "https://pics.example.invalid/sample-1.jpg",
        "https://pics.example.invalid/sample-2.jpg",
        "https://pics.example.invalid/sample-3.jpg",
    ]
