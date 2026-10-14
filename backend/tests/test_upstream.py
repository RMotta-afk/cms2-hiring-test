import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
import pytest

from project_editor.contracts import EditableFields, LinkedCompany, StoredProject
from project_editor.upstream import (
    HttpProjectStore,
    ProjectNotFound,
    UpstreamUnavailable,
    WriteUncertain,
)

T = TypeVar("T")


def raw_project() -> dict[str, object]:
    return {
        "id": "P-1001",
        "name": "Original",
        "sector": "energy",
        "country": "Chile",
        "stage": "idea",
        "key_dates": [{"label": "Tender", "date": "2027-01-01"}],
        "linked_companies": [{"name": "Owner Ltd", "role": "owner"}],
        "internal_code": "ignored by browser",
    }


def editable_fields() -> EditableFields:
    record = raw_project()
    return EditableFields.model_validate(
        {
            key: record[key]
            for key in ("name", "sector", "country", "stage", "key_dates")
        }
    )


def run_store(
    handler: Callable[[httpx.Request], httpx.Response],
    operation: Callable[[HttpProjectStore], Awaitable[T]],
) -> T:
    async def run() -> T:
        async with httpx.AsyncClient(
            base_url="http://upstream.test",
            headers={"X-Api-Key": "local-dev-key"},
            transport=httpx.MockTransport(handler),
        ) as client:
            return await operation(HttpProjectStore(client))

    return asyncio.run(run())


def test_list_and_get_parse_wide_records_but_keep_browser_projection_narrow() -> None:
    record = raw_project()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Api-Key"] == "local-dev-key"
        if request.url.path == "/projects":
            return httpx.Response(200, json=[record])
        return httpx.Response(200, json=record)

    listed = run_store(handler, lambda store: store.list_projects())
    fetched = run_store(handler, lambda store: store.get_project("P-1001"))
    assert isinstance(listed, list) and listed[0].id == "P-1001"
    assert isinstance(fetched, StoredProject)
    assert fetched.linked_companies[0].name == "Owner Ltd"
    assert "linked_companies" not in fetched.detail().model_dump()
    assert "internal_code" not in fetched.detail().model_dump()


def test_missing_and_unavailable_reads_are_distinct() -> None:
    def missing(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    def unavailable(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with pytest.raises(ProjectNotFound):
        run_store(missing, lambda store: store.get_project("P-0000"))
    with pytest.raises(UpstreamUnavailable):
        run_store(unavailable, lambda store: store.get_project("P-1001"))
    with pytest.raises(UpstreamUnavailable):
        run_store(unavailable, lambda store: store.list_projects())


def test_put_sends_full_replacement_with_latest_linked_companies() -> None:
    received: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["body"] = json.loads(request.content)
        return httpx.Response(200, json=raw_project() | received["body"])

    fields = editable_fields()
    companies = [LinkedCompany(name="Latest Ltd", role="developer")]
    saved = run_store(
        handler, lambda store: store.put_project("P-1001", fields, companies)
    )

    assert isinstance(saved, StoredProject)
    assert received["body"] == {
        "name": "Original",
        "sector": "energy",
        "country": "Chile",
        "stage": "idea",
        "key_dates": [{"label": "Tender", "date": "2027-01-01"}],
        "linked_companies": [{"name": "Latest Ltd", "role": "developer"}],
    }


def test_put_404_and_ambiguous_responses_have_distinct_errors() -> None:
    def missing(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    def uncertain(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(504)

    fields = editable_fields()
    companies = [LinkedCompany(name="Owner Ltd", role="owner")]
    with pytest.raises(ProjectNotFound):
        run_store(missing, lambda store: store.put_project("P-0000", fields, companies))
    with pytest.raises(WriteUncertain):
        run_store(
            uncertain, lambda store: store.put_project("P-1001", fields, companies)
        )


def test_transport_and_invalid_success_response_are_uncertain_puts() -> None:
    def network_error(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection lost")

    def invalid_json(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    fields = editable_fields()
    companies = [LinkedCompany(name="Owner Ltd", role="owner")]
    with pytest.raises(WriteUncertain):
        run_store(
            network_error,
            lambda store: store.put_project("P-1001", fields, companies),
        )
    with pytest.raises(WriteUncertain):
        run_store(
            invalid_json,
            lambda store: store.put_project("P-1001", fields, companies),
        )
