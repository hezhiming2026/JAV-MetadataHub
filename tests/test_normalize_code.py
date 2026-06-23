import pytest

from jav_metadatahub.normalizers import NormalizedCode, normalize_code


@pytest.mark.parametrize(
    ("raw_code", "expected"),
    [
        ("ABP-477", NormalizedCode("ABP-477", "ABP477", "ABP", "477")),
        ("abp477", NormalizedCode("abp477", "ABP477", "ABP", "477")),
        ("ABP_477", NormalizedCode("ABP_477", "ABP477", "ABP", "477")),
        ("ABP 477", NormalizedCode("ABP 477", "ABP477", "ABP", "477")),
        ("ABP.477", NormalizedCode("ABP.477", "ABP477", "ABP", "477")),
        ("  ABP-477  ", NormalizedCode("ABP-477", "ABP477", "ABP", "477")),
        ("ABP00477", NormalizedCode("ABP00477", "ABP00477", "ABP", "477")),
        ("IPX-001", NormalizedCode("IPX-001", "IPX001", "IPX", "1")),
        ("SSIS-001", NormalizedCode("SSIS-001", "SSIS001", "SSIS", "1")),
        ("h_123abc001", NormalizedCode("h_123abc001", "H123ABC001", "H123ABC", "1")),
        (
            "FC2-PPV-1234567",
            NormalizedCode("FC2-PPV-1234567", "FC2PPV1234567", "FC2PPV", "1234567"),
        ),
        ("title-only", NormalizedCode("title-only", "TITLEONLY", None, None)),
    ],
)
def test_normalize_code_parses_common_formats(
    raw_code: str,
    expected: NormalizedCode,
) -> None:
    assert normalize_code(raw_code) == expected


@pytest.mark.parametrize("raw_code", [None, "", "   "])
def test_normalize_code_returns_none_fields_for_empty_input(raw_code: str | None) -> None:
    assert normalize_code(raw_code) == NormalizedCode(None, None, None, None)


@pytest.mark.parametrize("raw_code", ["---", "___", "..."])
def test_normalize_code_returns_no_norm_when_separators_remove_everything(
    raw_code: str,
) -> None:
    assert normalize_code(raw_code) == NormalizedCode(raw_code, None, None, None)
