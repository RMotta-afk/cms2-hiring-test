"""HTTP boundary for the independently owned records service."""

from typing import Protocol

import httpx
from pydantic import TypeAdapter

from project_editor.contracts import EditableFields, LinkedCompany, StoredProject


class ProjectNotFound(Exception):
    pass


class UpstreamUnavailable(Exception):
    pass


class WriteUncertain(Exception):
    """A PUT may have landed even though we could not confirm it."""


class ProjectStore(Protocol):
    async def list_projects(self) -> list[StoredProject]: ...

    async def get_project(self, project_id: str) -> StoredProject: ...

    async def put_project(
        self,
        project_id: str,
        fields: EditableFields,
        linked_companies: list[LinkedCompany],
    ) -> StoredProject: ...


class HttpProjectStore:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def list_projects(self) -> list[StoredProject]:
        try:
            response = await self.client.get("/projects")
            if response.status_code != 200:
                raise UpstreamUnavailable()
            return TypeAdapter(list[StoredProject]).validate_python(response.json())
        except (httpx.RequestError, ValueError) as exc:
            raise UpstreamUnavailable() from exc

    async def get_project(self, project_id: str) -> StoredProject:
        try:
            response = await self.client.get(f"/projects/{project_id}")
            if response.status_code == 404:
                raise ProjectNotFound()
            if response.status_code != 200:
                raise UpstreamUnavailable()
            return StoredProject.model_validate(response.json())
        except (httpx.RequestError, ValueError) as exc:
            raise UpstreamUnavailable() from exc

    async def put_project(
        self,
        project_id: str,
        fields: EditableFields,
        linked_companies: list[LinkedCompany],
    ) -> StoredProject:
        body = fields.model_dump(mode="json")
        body["linked_companies"] = [
            company.model_dump() for company in linked_companies
        ]
        try:
            response = await self.client.put(f"/projects/{project_id}", json=body)
            if response.status_code == 404:
                raise ProjectNotFound()
            if response.status_code != 200:
                raise WriteUncertain()
            return StoredProject.model_validate(response.json())
        except (httpx.RequestError, ValueError) as exc:
            raise WriteUncertain() from exc
