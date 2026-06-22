from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.orm import Session

from jav_metadatahub.collectors.fanza_client import FanzaClientError, FanzaHTTPError
from jav_metadatahub.collectors.fanza_collector import FanzaCollector
from jav_metadatahub.db.models import CollectorRun
from jav_metadatahub.repositories.collector_runs import CollectorRunRepository


def make_collector() -> tuple[FanzaCollector, AsyncMock, Mock, Mock]:
    client = AsyncMock()
    source_records = Mock()
    collector_runs = Mock()
    collector_runs.start.return_value = CollectorRun(id=42, source="fanza", run_type="test")
    return (
        FanzaCollector(client, source_records, collector_runs),
        client,
        source_records,
        collector_runs,
    )


@pytest.mark.asyncio
async def test_collect_floor_list_writes_raw_source_record_and_run_counts() -> None:
    collector, client, source_records, collector_runs = make_collector()
    payload = {"result": {"floor": [{"id": "videoa"}]}}
    client.floor_list.return_value = payload

    result = await collector.collect_floor_list()

    assert result.request_count == 1
    assert result.success_count == 1
    assert result.failed_count == 0
    assert result.source_records_written == 1
    collector_runs.start.assert_called_once_with(
        source="fanza",
        run_type="floor_list",
        config={},
    )
    collector_runs.finish.assert_called_once_with(
        collector_runs.start.return_value,
        status="success",
        request_count=1,
        success_count=1,
        failed_count=0,
        error_message=None,
    )
    source_records.upsert.assert_called_once()
    kwargs = source_records.upsert.call_args.kwargs
    assert kwargs["source"] == "fanza"
    assert kwargs["source_key"] == "floor_list"
    assert kwargs["record_type"] == "floor_list"
    assert kwargs["source_url"] == "fanza://FloorList"
    assert kwargs["payload_type"] == "json"
    assert kwargs["raw_json"] == payload
    assert kwargs["fetch_status"] == "success"
    assert kwargs["parser_version"] is None
    assert kwargs["collector_run_id"] == 42
    assert isinstance(kwargs["checksum"], str)
    source_records.session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_collect_item_list_page_writes_page_and_item_records() -> None:
    collector, client, source_records, _collector_runs = make_collector()
    payload = {
        "result": {
            "total_count": "2",
            "items": [
                {"content_id": "cid-001", "product_id": "p1", "title": "Title 1"},
                {"content_id": " ", "product_id": "p2", "title": "Title 2"},
                {"title": "No identity"},
            ],
        }
    }
    client.item_list.return_value = payload

    result = await collector.collect_item_list_page(
        site="FANZA",
        service="digital",
        floor="videoa",
        keyword="ABP-477",
        hits=3,
        offset=1,
    )

    assert result.request_count == 1
    assert result.source_records_written == 4
    assert result.page_records_written == 1
    assert result.item_records_written == 3
    client.item_list.assert_awaited_once_with(
        site="FANZA",
        service="digital",
        floor="videoa",
        keyword="ABP-477",
        cid=None,
        hits=3,
        offset=1,
        sort="date",
        gte_date=None,
        lte_date=None,
    )

    calls = source_records.upsert.call_args_list
    page_kwargs = calls[0].kwargs
    assert page_kwargs["record_type"] == "search_result"
    assert page_kwargs["source_key"].startswith("search_result:")
    assert page_kwargs["source_url"].startswith("fanza://ItemList?")
    assert "keyword=ABP-477" in page_kwargs["source_url"]
    assert "api_id" not in page_kwargs["source_url"]
    assert "affiliate_id" not in page_kwargs["source_url"]

    item_keys = [call.kwargs["source_key"] for call in calls[1:]]
    assert item_keys[0] == "cid-001"
    assert item_keys[1] == "product_id:p2"
    assert item_keys[2].startswith("item_sha256:")
    assert all(call.kwargs["record_type"] == "work" for call in calls[1:])
    assert all(call.kwargs["raw_json"] in payload["result"]["items"] for call in calls[1:])


@pytest.mark.asyncio
async def test_collect_item_list_range_pages_until_max_pages() -> None:
    collector, client, _source_records, collector_runs = make_collector()
    client.item_list.side_effect = [
        {
            "result": {
                "total_count": "4",
                "items": [{"content_id": "cid-001"}, {"content_id": "cid-002"}],
            }
        },
        {
            "result": {
                "total_count": "4",
                "items": [{"content_id": "cid-003"}, {"content_id": "cid-004"}],
            }
        },
        {"result": {"total_count": "4", "items": []}},
    ]

    result = await collector.collect_item_list_range(hits=2, offset=1, max_pages=2)

    assert result.request_count == 2
    assert result.success_count == 2
    assert result.failed_count == 0
    assert [call.kwargs["offset"] for call in client.item_list.await_args_list] == [1, 3]
    collector_runs.finish.assert_called_once()
    assert collector_runs.finish.call_args.kwargs["request_count"] == 2
    assert collector_runs.finish.call_args.kwargs["success_count"] == 2


@pytest.mark.asyncio
async def test_collect_item_list_range_stops_on_short_page() -> None:
    collector, client, _source_records, _collector_runs = make_collector()
    client.item_list.return_value = {
        "result": {"total_count": "100", "items": [{"content_id": "cid-001"}]}
    }

    result = await collector.collect_item_list_range(hits=2, offset=1, max_pages=10)

    assert result.request_count == 1
    client.item_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_dry_run_calls_client_without_writing_records_or_runs() -> None:
    collector, client, source_records, collector_runs = make_collector()
    client.item_list.return_value = {"result": {"items": [{"content_id": "cid-001"}]}}

    result = await collector.collect_item_list_page(dry_run=True)

    assert result.request_count == 1
    assert result.source_records_written == 0
    source_records.upsert.assert_not_called()
    collector_runs.start.assert_not_called()
    collector_runs.finish.assert_not_called()


@pytest.mark.asyncio
async def test_page_failure_writes_failed_source_record_and_marks_run_failed() -> None:
    collector, client, source_records, collector_runs = make_collector()
    error = FanzaHTTPError(
        status_code=401,
        endpoint="/ItemList",
        params={
            "api_id": "fake-api-secret",
            "affiliate_id": "fake-affiliate-secret",
            "keyword": "ABP",
        },
        message="HTTP 401 for FANZA request",
    )
    client.item_list.side_effect = error

    with pytest.raises(FanzaHTTPError):
        await collector.collect_item_list_page(keyword="ABP")

    source_records.upsert.assert_called_once()
    kwargs = source_records.upsert.call_args.kwargs
    assert kwargs["fetch_status"] == "failed"
    assert kwargs["http_status"] == 401
    assert kwargs["record_type"] == "search_result"
    assert "fake-api-secret" not in str(kwargs["raw_json"])
    assert "fake-affiliate-secret" not in str(kwargs["raw_json"])
    collector_runs.finish.assert_called_once_with(
        collector_runs.start.return_value,
        status="failed",
        request_count=1,
        success_count=0,
        failed_count=1,
        error_message=str(error),
    )


@pytest.mark.asyncio
async def test_range_partial_failure_marks_run_partial_and_counts_logical_requests() -> None:
    collector, client, _source_records, collector_runs = make_collector()
    client.item_list.side_effect = [
        {
            "result": {
                "total_count": "10",
                "items": [{"content_id": "cid-001"}, {"content_id": "cid-002"}],
            }
        },
        FanzaClientError("transport failed"),
    ]

    with pytest.raises(FanzaClientError):
        await collector.collect_item_list_range(hits=2, offset=1, max_pages=3)

    assert [call.kwargs["offset"] for call in client.item_list.await_args_list] == [1, 3]
    collector_runs.finish.assert_called_once()
    finish_kwargs = collector_runs.finish.call_args.kwargs
    assert finish_kwargs["status"] == "partial"
    assert finish_kwargs["request_count"] == 2
    assert finish_kwargs["success_count"] == 1
    assert finish_kwargs["failed_count"] == 1


def test_collector_run_repository_start_and_finish_flush_without_commit() -> None:
    session = Mock(spec=Session)
    repository = CollectorRunRepository(session)

    run = repository.start(
        source="fanza",
        run_type="item_list_range",
        config={"hits": 100, "offset": 1},
    )
    repository.finish(
        run,
        status="success",
        request_count=2,
        success_count=2,
        failed_count=0,
        error_message=None,
    )

    assert run.source == "fanza"
    assert run.run_type == "item_list_range"
    assert run.status == "success"
    assert run.request_count == 2
    assert run.success_count == 2
    assert run.failed_count == 0
    assert run.finished_at is not None
    session.add.assert_called_once_with(run)
    assert session.flush.call_count == 2
    session.commit.assert_not_called()
