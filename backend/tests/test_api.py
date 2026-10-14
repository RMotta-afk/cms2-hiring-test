from collections.abc import Iterator
from typing import Literal

import pytest
from fastapi.testclient import TestClient

from project_editor.contracts import EditableFields, LinkedCompany, StoredProject
from project_editor.main import app, get_store
from project_editor.upstream import ProjectNotFound, WriteUncertain


class FakeStore:
    def __init__(self) -> None:
        self.project = StoredProject.model_validate(
            {
                "id": "P-1001",
                "name": "Original",
                "sector": "energy",
                "country": "Chile",
                "stage": "idea",
                "key_dates": [{"label": "Tender", "date": "2027-01-01"}],
                "linked_companies": [{"name": "Example SA", "role": "owner"}],
                "internal_code": "must not reach browser",
            }
        )
        self.put_count = 0
        self.timeout_mode: Literal["apply", "drop"] | None = None

    async def list_projects(self) -> list[StoredProject]:
        return [self.project.model_copy(deep=True)]

    async def get_project(self, project_id: str) -> StoredProject:
        if project_id != self.project.id:
            raise ProjectNotFound()
        return self.project.model_copy(deep=True)

    async def put_project(
        self,
        project_id: str,
        fields: EditableFields,
        linked_companies: list[LinkedCompany],
    ) -> StoredProject:
        if project_id != self.project.id:
            raise ProjectNotFound()
        self.put_count += 1
        saved = StoredProject(
            id=project_id,
            name=fields.name,
            sector=fields.sector,
            country=fields.country,
            stage=fields.stage,
            key_dates=fields.key_dates,
            linked_companies=linked_companies,
        )
        if self.timeout_mode != "drop":
            self.project = saved
        if self.timeout_mode is not None:
            raise WriteUncertain()
        return saved


@pytest.fixture
def api() -> Iterator[tuple[TestClient, FakeStore]]:
    store = FakeStore()
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as client:
        yield client, store
    app.dependency_overrides.clear()


def editable(project: dict[str, object]) -> dict[str, object]:
    return {
        key: project[key] for key in ("name", "sector", "country", "stage", "key_dates")
    }


def test_list_show_and_validation(api: tuple[TestClient, FakeStore]) -> None:
    client, _store = api
    listed = client.get("/api/projects")
    assert listed.status_code == 200
    assert listed.json() == {
        "projects": [
            {
                "id": "P-1001",
                "name": "Original",
                "sector": "energy",
                "country": "Chile",
                "stage": "idea",
            }
        ]
    }
    shown = client.get("/api/projects/P-1001")
    assert shown.status_code == 200
    project = shown.json()["project"]
    assert "linked_companies" not in project
    assert "internal_code" not in project
    assert client.get("/api/projects/unknown").status_code == 404

    bad = editable(project) | {"name": " ", "stage": "invalid"}
    assert (
        client.put(
            "/api/projects/P-1001", json={"base": editable(project), "proposed": bad}
        ).status_code
        == 422
    )


def test_different_fields_survive_and_latest_companies_are_preserved(
    api: tuple[TestClient, FakeStore],
) -> None:
    client, store = api
    base = editable(client.get("/api/projects/P-1001").json()["project"])
    first = base | {"name": "First editor"}
    second = base | {"country": "Peru"}

    assert (
        client.put(
            "/api/projects/P-1001", json={"base": base, "proposed": first}
        ).status_code
        == 200
    )
    store.project.linked_companies = [
        LinkedCompany(name="Importer Ltd", role="developer")
    ]
    response = client.put(
        "/api/projects/P-1001", json={"base": base, "proposed": second}
    )

    assert response.status_code == 200
    assert response.json()["project"]["name"] == "First editor"
    assert response.json()["project"]["country"] == "Peru"
    assert store.project.linked_companies[0].name == "Importer Ltd"


def test_same_field_conflicts_then_user_can_choose_mine(
    api: tuple[TestClient, FakeStore],
) -> None:
    client, store = api
    base = editable(client.get("/api/projects/P-1001").json()["project"])
    client.put(
        "/api/projects/P-1001",
        json={"base": base, "proposed": base | {"name": "First"}},
    )
    conflict = client.put(
        "/api/projects/P-1001",
        json={"base": base, "proposed": base | {"name": "Second"}},
    )

    assert conflict.status_code == 409
    assert conflict.json()["conflicting_fields"] == ["name"]
    assert conflict.json()["current"]["name"] == "First"
    assert store.put_count == 1

    rebased = editable(conflict.json()["current"])
    resolved = client.put(
        "/api/projects/P-1001",
        json={"base": rebased, "proposed": rebased | {"name": "Second"}},
    )
    assert resolved.status_code == 200
    assert resolved.json()["project"]["name"] == "Second"


def test_whole_key_date_list_conflicts(api: tuple[TestClient, FakeStore]) -> None:
    client, store = api
    base = editable(client.get("/api/projects/P-1001").json()["project"])
    first = base | {"key_dates": [{"label": "First", "date": "2027-02-01"}]}
    second = base | {"key_dates": [{"label": "Second", "date": "2027-03-01"}]}
    client.put("/api/projects/P-1001", json={"base": base, "proposed": first})
    response = client.put(
        "/api/projects/P-1001", json={"base": base, "proposed": second}
    )
    assert response.status_code == 409
    assert response.json()["conflicting_fields"] == ["key_dates"]
    assert store.project.key_dates[0].label == "First"


def test_key_dates_can_be_added_and_removed(api: tuple[TestClient, FakeStore]) -> None:
    client, store = api
    base = editable(client.get("/api/projects/P-1001").json()["project"])
    added = base | {
        "key_dates": [
            {"label": "Tender", "date": "2027-01-01"},
            {"label": "Construction", "date": "2028-01-01"},
        ]
    }
    response = client.put(
        "/api/projects/P-1001", json={"base": base, "proposed": added}
    )
    assert response.status_code == 200
    assert len(store.project.key_dates) == 2

    new_base = editable(response.json()["project"])
    removed = new_base | {"key_dates": []}
    response = client.put(
        "/api/projects/P-1001", json={"base": new_base, "proposed": removed}
    )
    assert response.status_code == 200
    assert store.project.key_dates == []


def test_invalid_date_is_rejected(api: tuple[TestClient, FakeStore]) -> None:
    client, store = api
    base = editable(client.get("/api/projects/P-1001").json()["project"])
    proposed = base | {"key_dates": [{"label": "Tender", "date": "2027-02-31"}]}
    response = client.put(
        "/api/projects/P-1001", json={"base": base, "proposed": proposed}
    )
    assert response.status_code == 422
    assert store.put_count == 0


@pytest.mark.parametrize("mode", ["apply", "drop"])
def test_timeout_is_ambiguous_and_never_retried(
    api: tuple[TestClient, FakeStore], mode: Literal["apply", "drop"]
) -> None:
    client, store = api
    store.timeout_mode = mode
    base = editable(client.get("/api/projects/P-1001").json()["project"])
    response = client.put(
        "/api/projects/P-1001",
        json={"base": base, "proposed": base | {"name": "Attempted"}},
    )
    assert response.status_code == 504
    assert response.json()["code"] == "write_uncertain"
    assert response.json()["observed"]["name"] == (
        "Attempted" if mode == "apply" else "Original"
    )
    assert store.put_count == 1
