from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from jav_metadatahub.normalizers import normalize_code

type FanzaItem = dict[str, Any]
type ObservationValue = dict[str, Any] | list[Any] | str | int | float | bool | None

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


class FanzaObservationCandidate(BaseModel):
    field_name: str
    field_value: ObservationValue


class FanzaParsedWork(BaseModel):
    source_key: str | None = None
    source_url: str | None = None
    observations: list[FanzaObservationCandidate] = Field(default_factory=list)


def _clean_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _first_string(item: FanzaItem, *field_names: str) -> str | None:
    for field_name in field_names:
        value = _clean_string(item.get(field_name))
        if value is not None:
            return value
    return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _name_values(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = _clean_string(value)
        return [cleaned] if cleaned is not None else []
    if isinstance(value, dict):
        cleaned = _clean_string(value.get("name"))
        return [cleaned] if cleaned is not None else []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(_name_values(item))
        return _dedupe(names)
    return []


_TOP_LEVEL_ALIASES = {
    "actress": ("actress", "actresses"),
    "actor": ("actor", "actors"),
    "director": ("director", "directors"),
    "genre": ("genre", "genres"),
    "maker": ("maker", "makers"),
    "label": ("label", "labels"),
    "series": ("series",),
}


def _iteminfo_values(item: FanzaItem, key: str) -> list[str]:
    values: list[str] = []
    iteminfo = item.get("iteminfo")
    if isinstance(iteminfo, dict):
        values.extend(_name_values(iteminfo.get(key)))
    for alias in _TOP_LEVEL_ALIASES.get(key, (key,)):
        values.extend(_name_values(item.get(alias)))
    return _dedupe(values)


def _first_iteminfo_value(item: FanzaItem, key: str) -> str | None:
    values = _iteminfo_values(item, key)
    return values[0] if values else None


def _safe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if _INTEGER_PATTERN.match(cleaned):
            return int(cleaned)
    return None


def _is_meaningful(value: ObservationValue) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | dict):
        return bool(value)
    return True


def _url_values(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = _clean_string(value)
        return [cleaned] if cleaned is not None else []
    if isinstance(value, list):
        list_urls: list[str] = []
        for item in value:
            list_urls.extend(_url_values(item))
        return list_urls
    if isinstance(value, dict):
        dict_urls: list[str] = []
        for nested_value in value.values():
            dict_urls.extend(_url_values(nested_value))
        return dict_urls
    return []


class FanzaParser:
    source = "fanza"
    parser_version = "fanza_parser_v1"

    def parse_work(self, item: FanzaItem) -> FanzaParsedWork:
        observations: list[FanzaObservationCandidate] = []

        content_id = _first_string(item, "content_id", "contentId", "contentID")
        product_id = _first_string(item, "product_id", "productId", "productID")
        dvd_id = _first_string(item, "dvd_id", "dvdId")
        code_original = self._code_original(item, dvd_id=dvd_id, product_id=product_id)

        self._add_observation(observations, "content_id", content_id)
        self._add_observation(observations, "product_id", product_id)
        self._add_observation(observations, "dvd_id", dvd_id)
        self._add_code_observations(observations, code_original)
        self._add_observation(observations, "title_ja", _first_string(item, "title", "title_ja"))
        self._add_observation(
            observations,
            "release_date",
            _first_string(item, "date", "release_date", "releaseDate"),
        )
        self._add_observation(observations, "runtime_minutes", self._runtime_minutes(item))
        self._add_observation(observations, "actresses", _iteminfo_values(item, "actress"))
        self._add_observation(observations, "actors", _iteminfo_values(item, "actor"))
        self._add_observation(observations, "directors", _iteminfo_values(item, "director"))
        self._add_observation(observations, "maker", _first_iteminfo_value(item, "maker"))
        self._add_observation(observations, "label", _first_iteminfo_value(item, "label"))
        self._add_observation(observations, "series", _first_iteminfo_value(item, "series"))
        self._add_observation(observations, "tags", self._tags(item))
        self._add_observation(observations, "media_urls", self._media_urls(item))
        source_url = _first_string(item, "URL", "url")
        self._add_observation(observations, "source_url", source_url)

        return FanzaParsedWork(
            source_key=content_id or product_id,
            source_url=source_url,
            observations=observations,
        )

    def _code_original(
        self,
        item: FanzaItem,
        *,
        dvd_id: str | None,
        product_id: str | None,
    ) -> str | None:
        return (
            _first_string(
                item,
                "maker_product",
                "makerProduct",
                "product_code",
                "productCode",
            )
            or dvd_id
            or product_id
        )

    def _runtime_minutes(self, item: FanzaItem) -> int | None:
        for field_name in ("volume", "runtime_minutes", "runtime", "duration"):
            runtime = _safe_int(item.get(field_name))
            if runtime is not None:
                return runtime
        return None

    def _tags(self, item: FanzaItem) -> list[str]:
        values: list[str] = []
        values.extend(_iteminfo_values(item, "genre"))
        values.extend(_name_values(item.get("tag")))
        values.extend(_name_values(item.get("tags")))
        return _dedupe(values)

    def _media_urls(self, item: FanzaItem) -> list[str]:
        urls: list[str] = []
        urls.extend(_url_values(item.get("imageURL")))
        urls.extend(_url_values(item.get("sampleImageURL")))
        for field_name in ("image_url", "imageUrl", "jacket_url", "jacketUrl"):
            urls.extend(_url_values(item.get(field_name)))
        return _dedupe(urls)

    def _add_code_observations(
        self,
        observations: list[FanzaObservationCandidate],
        code_original: str | None,
    ) -> None:
        normalized = normalize_code(code_original)
        self._add_observation(observations, "code_original", normalized.original)
        self._add_observation(observations, "code_norm", normalized.norm)
        self._add_observation(observations, "code_prefix", normalized.prefix)
        self._add_observation(observations, "code_number", normalized.number)

    def _add_observation(
        self,
        observations: list[FanzaObservationCandidate],
        field_name: str,
        field_value: ObservationValue,
    ) -> None:
        if not _is_meaningful(field_value):
            return
        observations.append(
            FanzaObservationCandidate(field_name=field_name, field_value=field_value)
        )
