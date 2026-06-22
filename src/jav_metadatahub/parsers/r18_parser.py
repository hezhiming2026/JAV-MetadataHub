from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, Field

from jav_metadatahub.normalizers import normalize_code
from jav_metadatahub.repositories.field_observations import ObservationValue

type R18Row = dict[str, Any]

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


class R18ObservationCandidate(BaseModel):
    field_name: str
    field_value: ObservationValue


class R18ParsedWork(BaseModel):
    source_key: str
    checksum: str
    source_url: str | None = None
    observations: list[R18ObservationCandidate] = Field(default_factory=list)


def stable_compact_json(row: R18Row) -> str:
    return json.dumps(
        row,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def stable_json_sha256(row: R18Row) -> str:
    return hashlib.sha256(stable_compact_json(row).encode("utf-8")).hexdigest()


def _clean_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _first_string(row: R18Row, *field_names: str) -> str | None:
    for field_name in field_names:
        value = _clean_string(row.get(field_name))
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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned_values: list[str] = []
    for item in value:
        cleaned = _clean_string(item)
        if cleaned is not None:
            cleaned_values.append(cleaned)
    return _dedupe(cleaned_values)


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


class R18DumpParser:
    source = "r18"
    parser_version = "r18_dump_parser_v1"

    def parse_work(self, row: R18Row) -> R18ParsedWork:
        checksum = stable_json_sha256(row)
        content_id = _first_string(row, "content_id", "contentId")
        dvd_id = _first_string(row, "dvd_id", "dvdId")
        source_key = content_id or dvd_id or f"row_sha256:{checksum}"

        observations: list[R18ObservationCandidate] = []

        self._add_observation(observations, "content_id", content_id)
        self._add_observation(observations, "dvd_id", dvd_id)
        self._add_code_observations(observations, dvd_id)
        self._add_observation(
            observations,
            "title_ja",
            _first_string(row, "title_ja", "japanese_title", "title"),
        )
        self._add_observation(
            observations,
            "title_en",
            _first_string(row, "title_en", "english_title"),
        )
        self._add_observation(observations, "release_date", _first_string(row, "release_date"))
        self._add_observation(
            observations,
            "runtime_minutes",
            self._runtime_minutes(row),
        )
        self._add_observation(observations, "actresses", _string_list(row.get("actresses")))
        self._add_observation(observations, "directors", _string_list(row.get("directors")))
        self._add_observation(observations, "maker", _first_string(row, "maker"))
        self._add_observation(observations, "label", _first_string(row, "label"))
        self._add_observation(observations, "series", _first_string(row, "series"))
        self._add_observation(observations, "tags", self._tags(row))
        self._add_observation(observations, "media_urls", self._media_urls(row))
        self._add_observation(
            observations,
            "description",
            _first_string(row, "description", "comment", "comments"),
        )

        return R18ParsedWork(
            source_key=source_key,
            checksum=checksum,
            source_url=_first_string(row, "url", "source_url"),
            observations=observations,
        )

    def _runtime_minutes(self, row: R18Row) -> int | None:
        for field_name in ("runtime_minutes", "runtime", "duration"):
            runtime = _safe_int(row.get(field_name))
            if runtime is not None:
                return runtime
        return None

    def _tags(self, row: R18Row) -> list[str]:
        return _dedupe(_string_list(row.get("categories")) + _string_list(row.get("tags")))

    def _media_urls(self, row: R18Row) -> list[str]:
        urls: list[str] = []
        for field_name in ("jacket_url", "cover_url", "image_url"):
            url = _clean_string(row.get(field_name))
            if url is not None:
                urls.append(url)
        urls.extend(_string_list(row.get("gallery_urls")))
        urls.extend(_string_list(row.get("sample_images")))
        return _dedupe(urls)

    def _add_code_observations(
        self,
        observations: list[R18ObservationCandidate],
        dvd_id: str | None,
    ) -> None:
        normalized = normalize_code(dvd_id)
        self._add_observation(observations, "code_original", normalized.original)
        self._add_observation(observations, "code_norm", normalized.norm)
        self._add_observation(observations, "code_prefix", normalized.prefix)
        self._add_observation(observations, "code_number", normalized.number)

    def _add_observation(
        self,
        observations: list[R18ObservationCandidate],
        field_name: str,
        field_value: ObservationValue,
    ) -> None:
        if not _is_meaningful(field_value):
            return
        observations.append(R18ObservationCandidate(field_name=field_name, field_value=field_value))
