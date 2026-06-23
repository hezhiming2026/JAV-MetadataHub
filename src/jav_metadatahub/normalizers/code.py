from __future__ import annotations

import re
from dataclasses import dataclass

SEPARATOR_PATTERN = re.compile(r"[\s_\-\.]+")
ALPHA_PREFIX_PATTERN = re.compile(r"^([A-Z]+)(\d+)$")
MIXED_PREFIX_PATTERN = re.compile(r"^([A-Z0-9]*?[A-Z]+)(\d+)$")


@dataclass(frozen=True)
class NormalizedCode:
    original: str | None
    norm: str | None
    prefix: str | None
    number: str | None


def normalize_code(code: str | None) -> NormalizedCode:
    if code is None:
        return NormalizedCode(None, None, None, None)

    original = code.strip()
    if not original:
        return NormalizedCode(None, None, None, None)

    norm = SEPARATOR_PATTERN.sub("", original.upper())
    if not norm:
        return NormalizedCode(original, None, None, None)

    for pattern in (ALPHA_PREFIX_PATTERN, MIXED_PREFIX_PATTERN):
        match = pattern.match(norm)
        if match:
            prefix, number = match.groups()
            return NormalizedCode(original, norm, prefix, number.lstrip("0") or "0")

    return NormalizedCode(original, norm, None, None)
