from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from jav_metadatahub.collectors.fanza_client import (
    FanzaClient,
    FanzaClientError,
    FanzaHTTPError,
)
from jav_metadatahub.db.models import CollectorRun
from jav_metadatahub.repositories.collector_runs import CollectorRunRepository
from jav_metadatahub.repositories.source_records import SourceRecordRepository

SOURCE = "fanza"


@dataclass(frozen=True)
class FanzaCollectionResult:
    request_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    source_records_written: int = 0
    page_records_written: int = 0
    item_records_written: int = 0


class FanzaCollector:
    """Collect FANZA/DMM raw API responses into source_records.

    Transaction semantics: this collector and its repositories only add/upsert/flush.
    They never commit. Failed source_records and collector_run updates are best-effort;
    if the caller re-raises and rolls back the transaction, those records will not persist.
    """

    def __init__(
        self,
        client: FanzaClient,
        source_records: SourceRecordRepository,
        collector_runs: CollectorRunRepository,
    ) -> None:
        self.client = client
        self.source_records = source_records
        self.collector_runs = collector_runs

    async def collect_floor_list(self, *, dry_run: bool = False) -> FanzaCollectionResult:
        run = self._start_run("floor_list", {}, dry_run=dry_run)
        try:
            payload = await self.client.floor_list()
            source_records_written = 0
            if not dry_run:
                self.source_records.upsert(
                    source=SOURCE,
                    source_key="floor_list",
                    record_type="floor_list",
                    source_url="fanza://FloorList",
                    payload_type="json",
                    raw_json=payload,
                    fetch_status="success",
                    parser_version=None,
                    checksum=stable_json_sha256(payload),
                    collector_run_id=_collector_run_id(run),
                )
                source_records_written = 1
            result = FanzaCollectionResult(
                request_count=1,
                success_count=1,
                source_records_written=source_records_written,
                page_records_written=source_records_written,
            )
            self._finish_run(run, result=result, status="success")
            return result
        except FanzaClientError as exc:
            result = FanzaCollectionResult(request_count=1, failed_count=1)
            if not dry_run:
                self._write_failed_record(
                    source_key="floor_list",
                    record_type="floor_list",
                    source_url="fanza://FloorList",
                    endpoint="/FloorList",
                    params={},
                    exc=exc,
                    run=run,
                )
            self._finish_run(run, result=result, status="failed", error_message=str(exc))
            raise

    async def collect_item_list_page(
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
        dry_run: bool = False,
    ) -> FanzaCollectionResult:
        params = _item_list_params(
            site=site,
            service=service,
            floor=floor,
            keyword=keyword,
            cid=cid,
            hits=hits,
            offset=offset,
            sort=sort,
            gte_date=gte_date,
            lte_date=lte_date,
        )
        run = self._start_run("item_list_page", params, dry_run=dry_run)
        try:
            result, _items, _total_count = await self._collect_item_list_page(
                params=params,
                run=run,
                dry_run=dry_run,
            )
            self._finish_run(run, result=result, status="success")
            return result
        except FanzaClientError as exc:
            result = FanzaCollectionResult(request_count=1, failed_count=1)
            if not dry_run:
                self._write_failed_item_list_record(params=params, exc=exc, run=run)
            self._finish_run(run, result=result, status="failed", error_message=str(exc))
            raise

    async def collect_item_list_range(
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
        max_pages: int = 1,
        dry_run: bool = False,
    ) -> FanzaCollectionResult:
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        base_params = _item_list_params(
            site=site,
            service=service,
            floor=floor,
            keyword=keyword,
            cid=cid,
            hits=hits,
            offset=offset,
            sort=sort,
            gte_date=gte_date,
            lte_date=lte_date,
        )
        run_config = dict(base_params)
        run_config["max_pages"] = max_pages
        run = self._start_run("item_list_range", run_config, dry_run=dry_run)
        aggregate = FanzaCollectionResult()
        current_offset = offset

        try:
            for _page_number in range(max_pages):
                page_params = dict(base_params)
                page_params["offset"] = current_offset
                page_result, items, total_count = await self._collect_item_list_page(
                    params=page_params,
                    run=run,
                    dry_run=dry_run,
                )
                aggregate = _merge_results(aggregate, page_result)
                if _should_stop_pagination(
                    payload_items=items,
                    hits=hits,
                    current_offset=current_offset,
                    total_count=total_count,
                ):
                    break
                next_offset = current_offset + hits
                if total_count is not None and next_offset > total_count:
                    break
                current_offset = next_offset
            self._finish_run(run, result=aggregate, status="success")
            return aggregate
        except FanzaClientError as exc:
            failed_result = FanzaCollectionResult(request_count=1, failed_count=1)
            aggregate = _merge_results(aggregate, failed_result)
            failed_params = dict(base_params)
            failed_params["offset"] = current_offset
            if not dry_run:
                self._write_failed_item_list_record(params=failed_params, exc=exc, run=run)
            status = "partial" if aggregate.success_count > 0 else "failed"
            self._finish_run(run, result=aggregate, status=status, error_message=str(exc))
            raise

    async def _collect_item_list_page(
        self,
        *,
        params: dict[str, str | int],
        run: CollectorRun | None,
        dry_run: bool,
    ) -> tuple[FanzaCollectionResult, list[Any], int | None]:
        payload = await self.client.item_list(
            site=str(params["site"]),
            service=_optional_str(params.get("service")),
            floor=_optional_str(params.get("floor")),
            keyword=_optional_str(params.get("keyword")),
            cid=_optional_str(params.get("cid")),
            hits=int(params["hits"]),
            offset=int(params["offset"]),
            sort=str(params["sort"]),
            gte_date=_optional_str(params.get("gte_date")),
            lte_date=_optional_str(params.get("lte_date")),
        )
        items = _extract_items(payload)
        total_count = _extract_total_count_from_payload(payload)
        source_records_written = 0
        page_records_written = 0
        item_records_written = 0
        if not dry_run:
            page_source_key = item_list_page_source_key(params)
            page_source_url = item_list_source_url(params)
            self.source_records.upsert(
                source=SOURCE,
                source_key=page_source_key,
                record_type="search_result",
                source_url=page_source_url,
                payload_type="json",
                raw_json=payload,
                fetch_status="success",
                parser_version=None,
                checksum=stable_json_sha256(payload),
                collector_run_id=_collector_run_id(run),
            )
            source_records_written += 1
            page_records_written += 1
            for item in items:
                if not isinstance(item, dict):
                    continue
                self.source_records.upsert(
                    source=SOURCE,
                    source_key=item_source_key(item),
                    record_type="work",
                    source_url=f"{page_source_url}#item={item_source_key(item)}",
                    payload_type="json",
                    raw_json=item,
                    fetch_status="success",
                    parser_version=None,
                    checksum=stable_json_sha256(item),
                    collector_run_id=_collector_run_id(run),
                )
                source_records_written += 1
                item_records_written += 1
        return (
            FanzaCollectionResult(
                request_count=1,
                success_count=1,
                source_records_written=source_records_written,
                page_records_written=page_records_written,
                item_records_written=item_records_written,
            ),
            items,
            total_count,
        )

    def _start_run(
        self,
        run_type: str,
        config: dict[str, Any],
        *,
        dry_run: bool,
    ) -> CollectorRun | None:
        if dry_run:
            return None
        return self.collector_runs.start(source=SOURCE, run_type=run_type, config=config)

    def _finish_run(
        self,
        run: CollectorRun | None,
        *,
        result: FanzaCollectionResult,
        status: str,
        error_message: str | None = None,
    ) -> None:
        if run is None:
            return
        self.collector_runs.finish(
            run,
            status=status,
            request_count=result.request_count,
            success_count=result.success_count,
            failed_count=result.failed_count,
            error_message=error_message,
        )

    def _write_failed_item_list_record(
        self,
        *,
        params: dict[str, str | int],
        exc: FanzaClientError,
        run: CollectorRun | None,
    ) -> None:
        self._write_failed_record(
            source_key=item_list_page_source_key(params),
            record_type="search_result",
            source_url=item_list_source_url(params),
            endpoint="/ItemList",
            params=params,
            exc=exc,
            run=run,
        )

    def _write_failed_record(
        self,
        *,
        source_key: str,
        record_type: str,
        source_url: str,
        endpoint: str,
        params: dict[str, Any],
        exc: FanzaClientError,
        run: CollectorRun | None,
    ) -> None:
        status_code = exc.status_code if isinstance(exc, FanzaHTTPError) else None
        raw_json = {
            "endpoint": endpoint,
            "params": dict(params),
            "error_class": exc.__class__.__name__,
            "error_message": str(exc),
        }
        self.source_records.upsert(
            source=SOURCE,
            source_key=source_key,
            record_type=record_type,
            source_url=source_url,
            payload_type="json",
            raw_json=raw_json,
            http_status=status_code,
            fetch_status="failed",
            error_message=str(exc),
            parser_version=None,
            checksum=stable_json_sha256(raw_json),
            collector_run_id=_collector_run_id(run),
        )


def stable_json_sha256(payload: Any) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def item_list_page_source_key(params: dict[str, str | int]) -> str:
    identity = {"endpoint": "ItemList", "params": params}
    return f"search_result:{stable_json_sha256(identity)}"


def item_list_source_url(params: dict[str, str | int]) -> str:
    query = urlencode(sorted(params.items()))
    return f"fanza://ItemList?{query}"


def item_source_key(item: dict[str, Any]) -> str:
    content_id = _non_empty_string(item.get("content_id"))
    if content_id is not None:
        return content_id
    product_id = _non_empty_string(item.get("product_id"))
    if product_id is not None:
        return f"product_id:{product_id}"
    return f"item_sha256:{stable_json_sha256(item)}"


def _stable_json(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _item_list_params(
    *,
    site: str,
    service: str | None,
    floor: str | None,
    keyword: str | None,
    cid: str | None,
    hits: int,
    offset: int,
    sort: str,
    gte_date: str | None,
    lte_date: str | None,
) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "site": site,
        "hits": hits,
        "offset": offset,
        "sort": sort,
    }
    optional = {
        "service": service,
        "floor": floor,
        "keyword": keyword,
        "cid": cid,
        "gte_date": gte_date,
        "lte_date": lte_date,
    }
    for key, value in optional.items():
        if value is not None:
            params[key] = value
    return params


def _extract_items(payload: dict[str, Any]) -> list[Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return []
    items = result.get("items")
    if not isinstance(items, list):
        return []
    return items


def _extract_total_count_from_payload(payload: dict[str, Any]) -> int | None:
    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    total_count = result.get("total_count")
    if total_count is None:
        return None
    try:
        parsed = int(total_count)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _should_stop_pagination(
    *,
    payload_items: list[Any],
    hits: int,
    current_offset: int,
    total_count: int | None,
) -> bool:
    if not payload_items:
        return True
    if len(payload_items) < hits:
        return True
    return total_count is not None and current_offset + hits > total_count


def _merge_results(
    left: FanzaCollectionResult,
    right: FanzaCollectionResult,
) -> FanzaCollectionResult:
    return FanzaCollectionResult(
        request_count=left.request_count + right.request_count,
        success_count=left.success_count + right.success_count,
        failed_count=left.failed_count + right.failed_count,
        source_records_written=left.source_records_written + right.source_records_written,
        page_records_written=left.page_records_written + right.page_records_written,
        item_records_written=left.item_records_written + right.item_records_written,
    )


def _collector_run_id(run: CollectorRun | None) -> int | None:
    if run is None:
        return None
    run_id = run.id
    return run_id if isinstance(run_id, int) and not isinstance(run_id, bool) else None


def _non_empty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
