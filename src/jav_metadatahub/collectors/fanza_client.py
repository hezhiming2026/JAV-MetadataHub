from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_fixed

from jav_metadatahub.config import get_settings

logger = logging.getLogger(__name__)

FANZA_ENDPOINTS: dict[str, str] = {
    "floor_list": "/FloorList",
    "item_list": "/ItemList",
    "actress_search": "/ActressSearch",
    "maker_search": "/MakerSearch",
    "genre_search": "/GenreSearch",
    "series_search": "/SeriesSearch",
}

SECRET_PARAM_NAMES = frozenset({"api_id", "affiliate_id"})
JsonObject = dict[str, Any]
Params = dict[str, str | int | float | bool]
SleepCallable = Callable[[float], Awaitable[None]]


class FanzaClientError(Exception):
    """Base error for FANZA/DMM API client failures."""


class FanzaHTTPError(FanzaClientError):
    """HTTP failure with credentials redacted from exposed request params."""

    def __init__(
        self,
        *,
        status_code: int,
        endpoint: str,
        params: Mapping[str, Any],
        message: str,
    ) -> None:
        self.status_code = status_code
        self.endpoint = endpoint
        self.params = redact_fanza_params(params)
        super().__init__(
            f"{message}; status_code={status_code}; endpoint={endpoint}; params={self.params}"
        )


def redact_fanza_params(params: Mapping[str, Any]) -> dict[str, Any]:
    return {key: "***" if key in SECRET_PARAM_NAMES else value for key, value in params.items()}


def should_retry_fanza_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or status_code >= 500
    return False


def _clean_required_secret(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


class FanzaClient:
    """Async FANZA/DMM API client.

    The client only constructs and executes metadata API requests. It does not collect,
    persist, parse, or promote records.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_id: str | None = None,
        affiliate_id: str | None = None,
        timeout_seconds: float | None = None,
        max_attempts: int | None = None,
        rate_limit_per_second: float | None = None,
        retry_wait_seconds: float = 0.5,
        client: httpx.AsyncClient | None = None,
        sleep: SleepCallable = asyncio.sleep,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url if base_url is not None else settings.fanza_base_url).strip()
        if not self.base_url:
            raise ValueError("base_url is required")
        self.api_id = _clean_required_secret(
            api_id if api_id is not None else settings.fanza_api_id,
            "api_id",
        )
        self.affiliate_id = _clean_required_secret(
            affiliate_id if affiliate_id is not None else settings.fanza_affiliate_id,
            "affiliate_id",
        )
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.collector_timeout_seconds
        )
        self.max_attempts = (
            max_attempts if max_attempts is not None else settings.collector_max_retries
        )
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.rate_limit_per_second = (
            rate_limit_per_second
            if rate_limit_per_second is not None
            else settings.collector_default_rate_limit_per_second
        )
        self.retry_wait_seconds = retry_wait_seconds
        self._sleep = sleep
        self._client = client or httpx.AsyncClient(timeout=self.timeout_seconds)
        self._owns_client = client is None
        self._rate_limit_lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def __aenter__(self) -> FanzaClient:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def floor_list(self) -> JsonObject:
        return await self._request_endpoint("floor_list", {})

    async def item_list(
        self,
        *,
        site: str = "FANZA",
        service: str | None = None,
        floor: str | None = None,
        keyword: str | None = None,
        cid: str | None = None,
        hits: int = 100,
        offset: int = 1,
        sort: str = "date",
        gte_date: str | None = None,
        lte_date: str | None = None,
    ) -> JsonObject:
        self._validate_hits(hits)
        self._validate_offset(offset)
        return await self._request_endpoint(
            "item_list",
            {
                "site": site,
                "service": service,
                "floor": floor,
                "keyword": keyword,
                "cid": cid,
                "hits": hits,
                "offset": offset,
                "sort": sort,
                "gte_date": gte_date,
                "lte_date": lte_date,
            },
        )

    async def actress_search(
        self,
        *,
        keyword: str | None = None,
        hits: int = 100,
        offset: int = 1,
    ) -> JsonObject:
        self._validate_hits(hits)
        self._validate_offset(offset)
        return await self._request_endpoint(
            "actress_search",
            {"keyword": keyword, "hits": hits, "offset": offset},
        )

    async def maker_search(
        self,
        *,
        floor_id: int | None = None,
        keyword: str | None = None,
        hits: int = 100,
        offset: int = 1,
    ) -> JsonObject:
        self._validate_hits(hits)
        self._validate_offset(offset)
        return await self._request_endpoint(
            "maker_search",
            {"floor_id": floor_id, "keyword": keyword, "hits": hits, "offset": offset},
        )

    async def genre_search(self, *, floor_id: int | None = None) -> JsonObject:
        return await self._request_endpoint("genre_search", {"floor_id": floor_id})

    async def series_search(
        self,
        *,
        floor_id: int | None = None,
        keyword: str | None = None,
        hits: int = 100,
        offset: int = 1,
    ) -> JsonObject:
        self._validate_hits(hits)
        self._validate_offset(offset)
        return await self._request_endpoint(
            "series_search",
            {"floor_id": floor_id, "keyword": keyword, "hits": hits, "offset": offset},
        )

    def _build_url(self, endpoint_path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"

    async def _request_endpoint(
        self,
        endpoint_key: str,
        params: Mapping[str, str | int | float | bool | None],
    ) -> JsonObject:
        endpoint_path = FANZA_ENDPOINTS[endpoint_key]
        request_params = self._prepare_params(params)
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(should_retry_fanza_error),
                stop=stop_after_attempt(self.max_attempts),
                wait=wait_fixed(self.retry_wait_seconds),
                reraise=True,
            ):
                with attempt:
                    return await self._request_once(endpoint_path, request_params)
        except httpx.HTTPStatusError as exc:
            redacted_params = redact_fanza_params(request_params)
            logger.warning(
                "FANZA request failed endpoint=%s status_code=%s params=%s error_class=%s",
                endpoint_path,
                exc.response.status_code,
                redacted_params,
                exc.__class__.__name__,
                extra={
                    "endpoint": endpoint_path,
                    "status_code": exc.response.status_code,
                    "params": redacted_params,
                    "error_class": exc.__class__.__name__,
                },
            )
            raise FanzaHTTPError(
                status_code=exc.response.status_code,
                endpoint=endpoint_path,
                params=request_params,
                message=f"HTTP {exc.response.status_code} for FANZA request",
            ) from exc
        except httpx.HTTPError as exc:
            redacted_params = redact_fanza_params(request_params)
            logger.warning(
                "FANZA request failed endpoint=%s params=%s error_class=%s",
                endpoint_path,
                redacted_params,
                exc.__class__.__name__,
                extra={
                    "endpoint": endpoint_path,
                    "params": redacted_params,
                    "error_class": exc.__class__.__name__,
                },
            )
            raise FanzaClientError(
                f"FANZA request failed; endpoint={endpoint_path}; params={redacted_params}; "
                f"error_class={exc.__class__.__name__}"
            ) from exc
        raise FanzaClientError("FANZA request failed without returning a response")

    async def _request_once(self, endpoint_path: str, params: Params) -> JsonObject:
        await self._wait_for_rate_limit()
        url = self._build_url(endpoint_path)
        logger.debug(
            "FANZA request",
            extra={"endpoint": endpoint_path, "params": redact_fanza_params(params)},
        )
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:
            raise FanzaClientError(
                f"FANZA response is not valid JSON; endpoint={endpoint_path}; "
                f"params={redact_fanza_params(params)}"
            ) from exc
        if not isinstance(data, dict):
            raise FanzaClientError(
                f"FANZA response JSON must be an object; endpoint={endpoint_path}; "
                f"params={redact_fanza_params(params)}"
            )
        return data

    async def _wait_for_rate_limit(self) -> None:
        if self.rate_limit_per_second <= 0:
            return
        interval = 1.0 / self.rate_limit_per_second
        async with self._rate_limit_lock:
            now = time.monotonic()
            delay = max(0.0, self._next_request_at - now)
            if delay > 0:
                await self._sleep(delay)
            self._next_request_at = time.monotonic() + interval

    def _prepare_params(
        self,
        params: Mapping[str, str | int | float | bool | None],
    ) -> Params:
        prepared: Params = {
            "api_id": self.api_id,
            "affiliate_id": self.affiliate_id,
            "output": "json",
        }
        for key, value in params.items():
            if value is not None:
                prepared[key] = value
        return prepared

    @staticmethod
    def _validate_hits(hits: int) -> None:
        if hits < 1 or hits > 100:
            raise ValueError("hits must be between 1 and 100")

    @staticmethod
    def _validate_offset(offset: int) -> None:
        if offset < 1:
            raise ValueError("offset must be at least 1")
