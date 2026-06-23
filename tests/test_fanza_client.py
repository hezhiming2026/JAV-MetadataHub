import logging
import re
from collections.abc import Generator
from typing import Any

import httpx
import pytest
import respx

from jav_metadatahub.collectors.fanza_client import (
    FanzaClient,
    FanzaHTTPError,
    redact_fanza_params,
    should_retry_fanza_error,
)

API_ID = "fake-api-secret"
AFFILIATE_ID = "fake-affiliate-secret"
BASE_URL = "https://api.example.test/affiliate/v3"
_ACTIVE_RESPX: respx.MockRouter | None = None


@pytest.fixture(autouse=True)
def respx_router() -> Generator[respx.MockRouter]:
    global _ACTIVE_RESPX
    with respx.mock(assert_all_mocked=True) as router:
        _ACTIVE_RESPX = router
        yield router
    _ACTIVE_RESPX = None


def make_client(**kwargs: Any) -> FanzaClient:
    return FanzaClient(
        base_url=kwargs.pop("base_url", BASE_URL),
        api_id=kwargs.pop("api_id", API_ID),
        affiliate_id=kwargs.pop("affiliate_id", AFFILIATE_ID),
        rate_limit_per_second=kwargs.pop("rate_limit_per_second", 0),
        max_attempts=kwargs.pop("max_attempts", 1),
        retry_wait_seconds=kwargs.pop("retry_wait_seconds", 0),
        **kwargs,
    )


def mock_endpoint(endpoint: str, **kwargs: Any) -> respx.Route:
    if _ACTIVE_RESPX is None:
        raise RuntimeError("respx router is not active")
    return _ACTIVE_RESPX.get(url__regex=rf"^{re.escape(BASE_URL)}/{endpoint}(?:\?.*)?$").mock(
        **kwargs
    )


@pytest.mark.asyncio
async def test_item_list_constructs_expected_request_params() -> None:
    route = mock_endpoint(
        "ItemList", return_value=httpx.Response(200, json={"result": {"status": 200}})
    )
    client = make_client(base_url=f"{BASE_URL}/")

    result = await client.item_list(
        service="digital",
        floor="videoa",
        keyword="ABP-477",
        cid="cid001",
        hits=50,
        offset=2,
        sort="rank",
        gte_date="2026-01-01T00:00:00",
        lte_date="2026-01-31T23:59:59",
    )

    assert result == {"result": {"status": 200}}
    assert route.called
    params = route.calls.last.request.url.params
    assert params["api_id"] == API_ID
    assert params["affiliate_id"] == AFFILIATE_ID
    assert params["output"] == "json"
    assert params["site"] == "FANZA"
    assert params["service"] == "digital"
    assert params["floor"] == "videoa"
    assert params["keyword"] == "ABP-477"
    assert params["cid"] == "cid001"
    assert params["hits"] == "50"
    assert params["offset"] == "2"
    assert params["sort"] == "rank"
    assert params["gte_date"] == "2026-01-01T00:00:00"
    assert params["lte_date"] == "2026-01-31T23:59:59"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "endpoint", "kwargs", "expected_params"),
    [
        ("floor_list", "FloorList", {}, {}),
        (
            "actress_search",
            "ActressSearch",
            {"keyword": "actor", "hits": 20, "offset": 3},
            {"keyword": "actor", "hits": "20", "offset": "3"},
        ),
        (
            "maker_search",
            "MakerSearch",
            {"floor_id": 43, "keyword": "maker", "hits": 10, "offset": 4},
            {"floor_id": "43", "keyword": "maker", "hits": "10", "offset": "4"},
        ),
        ("genre_search", "GenreSearch", {"floor_id": 43}, {"floor_id": "43"}),
        (
            "series_search",
            "SeriesSearch",
            {"floor_id": 43, "keyword": "series", "hits": 5, "offset": 6},
            {"floor_id": "43", "keyword": "series", "hits": "5", "offset": "6"},
        ),
    ],
)
async def test_public_methods_use_expected_endpoints_and_params(
    method_name: str,
    endpoint: str,
    kwargs: dict[str, Any],
    expected_params: dict[str, str],
) -> None:
    route = mock_endpoint(endpoint, return_value=httpx.Response(200, json={}))
    client = make_client()

    await getattr(client, method_name)(**kwargs)

    assert route.called
    params = route.calls.last.request.url.params
    assert params["api_id"] == API_ID
    assert params["affiliate_id"] == AFFILIATE_ID
    assert params["output"] == "json"
    for key, value in expected_params.items():
        assert params[key] == value


def test_build_url_normalizes_base_and_endpoint_slashes() -> None:
    client = make_client(base_url=f"{BASE_URL}/")

    assert client._build_url("/ItemList") == f"{BASE_URL}/ItemList"
    assert client._build_url("ItemList") == f"{BASE_URL}/ItemList"


@pytest.mark.parametrize("field_name", ["api_id", "affiliate_id"])
@pytest.mark.parametrize("bad_value", [None, "", "   "])
def test_init_rejects_blank_credentials(field_name: str, bad_value: str | None) -> None:
    kwargs = {"api_id": API_ID, "affiliate_id": AFFILIATE_ID}
    kwargs[field_name] = bad_value

    with pytest.raises(ValueError, match=field_name):
        make_client(**kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("hits", [0, 101])
async def test_hits_must_be_between_1_and_100(hits: int) -> None:
    client = make_client()

    with pytest.raises(ValueError, match="hits"):
        await client.item_list(hits=hits)


@pytest.mark.asyncio
async def test_offset_must_be_positive() -> None:
    client = make_client()

    with pytest.raises(ValueError, match="offset"):
        await client.item_list(offset=0)


@pytest.mark.asyncio
async def test_retries_timeout_and_transport_errors_then_succeeds() -> None:
    route = mock_endpoint(
        "FloorList",
        side_effect=[
            httpx.TimeoutException("timeout"),
            httpx.TransportError("transport failed"),
            httpx.Response(200, json={"ok": True}),
        ],
    )
    client = make_client(max_attempts=3)

    result = await client.floor_list()

    assert result == {"ok": True}
    assert route.call_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [429, 500, 503])
async def test_retries_transient_http_status_then_succeeds(status_code: int) -> None:
    route = mock_endpoint(
        "FloorList",
        side_effect=[
            httpx.Response(status_code, json={"error": "transient"}),
            httpx.Response(200, json={"ok": True}),
        ],
    )
    client = make_client(max_attempts=2)

    result = await client.floor_list()

    assert result == {"ok": True}
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_max_attempts_is_total_request_count() -> None:
    route = mock_endpoint(
        "FloorList",
        side_effect=[
            httpx.Response(500, json={"error": "one"}),
            httpx.Response(500, json={"error": "two"}),
            httpx.Response(500, json={"error": "three"}),
        ],
    )
    client = make_client(max_attempts=3)

    with pytest.raises(FanzaHTTPError) as exc_info:
        await client.floor_list()

    assert exc_info.value.status_code == 500
    assert route.call_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
async def test_does_not_retry_non_transient_client_errors(status_code: int) -> None:
    route = mock_endpoint(
        "FloorList", return_value=httpx.Response(status_code, json={"error": "client"})
    )
    client = make_client(max_attempts=3)

    with pytest.raises(FanzaHTTPError) as exc_info:
        await client.floor_list()

    assert exc_info.value.status_code == status_code
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_non_json_response_raises_client_error() -> None:
    mock_endpoint("FloorList", return_value=httpx.Response(200, content=b"not json"))
    client = make_client()

    with pytest.raises(Exception, match="JSON"):
        await client.floor_list()


def test_retry_predicate_only_allows_transient_failures() -> None:
    request = httpx.Request("GET", f"{BASE_URL}/FloorList")
    response_429 = httpx.Response(429, request=request)
    response_500 = httpx.Response(500, request=request)
    response_404 = httpx.Response(404, request=request)

    assert should_retry_fanza_error(httpx.TimeoutException("timeout"))
    assert should_retry_fanza_error(httpx.TransportError("transport"))
    assert should_retry_fanza_error(
        httpx.HTTPStatusError("too many requests", request=request, response=response_429)
    )
    assert should_retry_fanza_error(
        httpx.HTTPStatusError("server error", request=request, response=response_500)
    )
    assert not should_retry_fanza_error(
        httpx.HTTPStatusError("not found", request=request, response=response_404)
    )
    assert not should_retry_fanza_error(ValueError("bad input"))


def test_redacts_credentials_in_params_and_error_string() -> None:
    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "keyword": "ABP-477",
    }

    redacted = redact_fanza_params(params)
    error = FanzaHTTPError(
        status_code=401,
        endpoint="/ItemList",
        params=params,
        message="HTTP 401 for FANZA request",
    )

    assert redacted["api_id"] == "***"
    assert redacted["affiliate_id"] == "***"
    assert redacted["keyword"] == "ABP-477"
    assert API_ID not in str(error)
    assert AFFILIATE_ID not in str(error)
    assert error.params["api_id"] == "***"
    assert error.params["affiliate_id"] == "***"


@pytest.mark.asyncio
async def test_logs_redacted_params_on_http_error(caplog: pytest.LogCaptureFixture) -> None:
    mock_endpoint("FloorList", return_value=httpx.Response(401, json={}))
    client = make_client(max_attempts=1)

    with caplog.at_level(logging.WARNING, logger="jav_metadatahub.collectors.fanza_client"):
        with pytest.raises(FanzaHTTPError):
            await client.floor_list()

    log_text = caplog.text
    assert API_ID not in log_text
    assert AFFILIATE_ID not in log_text
    assert "***" in log_text
