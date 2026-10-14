"""Browser-facing project API."""

import os
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from project_editor.contracts import (
    ConflictResponse,
    ProjectListResponse,
    ProjectResponse,
    SaveRequest,
    UncertainResponse,
)
from project_editor.merge import merge_edit
from project_editor.upstream import (
    HttpProjectStore,
    ProjectNotFound,
    ProjectStore,
    UpstreamUnavailable,
    WriteUncertain,
)


async def get_store() -> AsyncIterator[ProjectStore]:
    async with httpx.AsyncClient(
        base_url=os.getenv("UPSTREAM_URL", "http://127.0.0.1:8081"),
        headers={"X-Api-Key": os.getenv("UPSTREAM_API_KEY", "local-dev-key")},
        timeout=5.0,
        trust_env=False,
    ) as client:
        yield HttpProjectStore(client)


StoreDependency = Annotated[ProjectStore, Depends(get_store)]
app = FastAPI(title="Project Editor API")


@app.exception_handler(ProjectNotFound)
async def not_found(_request: Request, _exc: ProjectNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"code": "project_not_found"})


@app.exception_handler(UpstreamUnavailable)
async def unavailable(_request: Request, _exc: UpstreamUnavailable) -> JSONResponse:
    return JSONResponse(status_code=502, content={"code": "upstream_unavailable"})


@app.get("/api/projects", response_model=ProjectListResponse)
async def list_projects(store: StoreDependency) -> ProjectListResponse:
    projects = await store.list_projects()
    return ProjectListResponse(projects=[project.summary() for project in projects])


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def show_project(project_id: str, store: StoreDependency) -> ProjectResponse:
    project = await store.get_project(project_id)
    return ProjectResponse(project=project.detail())


@app.put(
    "/api/projects/{project_id}",
    response_model=ProjectResponse,
    responses={409: {"model": ConflictResponse}, 504: {"model": UncertainResponse}},
)
async def save_project(
    project_id: str, update: SaveRequest, store: StoreDependency
) -> ProjectResponse | JSONResponse:
    current = await store.get_project(project_id)
    result = merge_edit(update.base, update.proposed, current)
    if result.conflicts:
        conflict = ConflictResponse(
            current=current.detail(), conflicting_fields=result.conflicts
        )
        return JSONResponse(status_code=409, content=conflict.model_dump(mode="json"))
    if not result.changed:
        return ProjectResponse(project=current.detail())
    try:
        saved = await store.put_project(
            project_id, result.merged, current.linked_companies
        )
    except WriteUncertain:
        try:
            observed = (await store.get_project(project_id)).detail()
        except (ProjectNotFound, UpstreamUnavailable):
            observed = None
        uncertain = UncertainResponse(observed=observed)
        return JSONResponse(status_code=504, content=uncertain.model_dump(mode="json"))
    return ProjectResponse(project=saved.detail())


def run() -> None:
    uvicorn.run("project_editor.main:app", host="127.0.0.1", port=8080, reload=False)
