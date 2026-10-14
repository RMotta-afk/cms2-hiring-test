# Project editor implementation plan

Status: the MVP is implemented. The task DAG now has two independent agent queues for reconciling and extending that baseline. Pending statuses track work in those queues, not missing runtime behavior.

This document is the human entry point. The normative architecture, allowed dependencies, API payloads, and worktree ownership live in [the SDD](sdd/architecture.md), [API contract](sdd/api-contract.md), and [worktree rules](sdd/worktrees.md). The machine-readable task DAG is in [`.context/decomposition.json`](../.context/decomposition.json). Backend task files are under [`.context/tasks/backend/`](../.context/tasks/backend/) and frontend task files under [`.context/tasks/frontend/`](../.context/tasks/frontend/).

## Goal and boundary

Deliver one working path through the fixed upstream API: list projects, show one project, and save edits to `name`, `sector`, `country`, `stage`, and `key_dates`. Two stale editors must be able to save changes to different fields without losing either change; overlapping changes must prompt the second editor. The browser calls only our backend. The backend keeps the upstream API key. The code remains small enough to explain and change live.

The upstream folder is read-only. Its `PUT` requires all six editable fields and replaces both lists. It has no revision or conditional write, and a `504` may follow an applied save. Production has three backend instances and an importer that bypasses them. These facts determine the contract and the explicit safety limit below.

## Browser-facing contract

All responses use JSON. The three routes are:

| Method and path | Request | Success response |
| --- | --- | --- |
| `GET /api/projects` | none | `200 { "projects": ProjectSummary[] }` |
| `GET /api/projects/{id}` | none | `200 { "project": ProjectDetail }` |
| `PUT /api/projects/{id}` | `{ "base": EditableFields, "proposed": EditableFields }` | `200 { "project": ProjectDetail }` |

`ProjectSummary = { id, name, sector, country, stage }`. `ProjectDetail = { id, ...EditableFields }`. `EditableFields = { name, sector, country, stage, key_dates }`. `key_dates` is an array of `{ label: string, date: YYYY-MM-DD }`. `sector` and `stage` use the exact enum values in `upstream/records_api/seed.py`. The frontend may add, edit, and remove date rows. `linked_companies` is intentionally absent from browser data; the backend retains its latest upstream value for a full `PUT`.

Relevant non-success responses:

| Status | Body | Meaning |
| --- | --- | --- |
| `404` | `{ "code": "project_not_found" }` | Unknown project ID |
| `409` | `{ "code": "edit_conflict", "current": ProjectDetail, "conflicting_fields": EditableFieldName[] }` | Overlapping edits; no `PUT` was sent |
| `422` | FastAPI validation error | Invalid request or date |
| `502` | `{ "code": "upstream_unavailable" }` | Read failed or upstream data was invalid |
| `504` | `{ "code": "write_uncertain", "observed": ProjectDetail | null }` | A write may have landed; review before another save |

`EditableFieldName` is one of `name`, `sector`, `country`, `stage`, or `key_dates`. Both `base` and `proposed` are required because the backend has no stored version of the form. The backend validates enums, nonblank text, date values, shape, and unexpected fields. Zod mirrors the browser-facing shapes and validates before a request and after a response. The backend Pydantic models remain authoritative.

## Save decision

Immediately before a save, fetch the latest full upstream project. For each editable field:

| Comparison | Action |
| --- | --- |
| `proposed == base` | Keep current; the editor did not change this field |
| `current == base` | Apply proposed |
| `current == proposed` | Keep current; both editors reached the same value |
| All other cases | Return `409` for that field |

If any fields conflict, send no upstream `PUT`. The UI shows current and mine for each conflicting field. The editor chooses per field, including one choice for the entire `key_dates` list, then the UI rebases on `current` and resubmits. Date entries have labels but no stable IDs; treating the list as one field avoids guessing whether a row was renamed, reordered, or removed. Nonconflicting changes remain in the resubmitted draft.

For a conflict-free save, send all upstream-required fields: merged core values and dates plus `linked_companies` from the fresh read. Skip the `PUT` when the merged editable values already equal current. After a `504` or lost response, never retry automatically. Attempt one diagnostic read and return the observed snapshot or null, while keeping the outcome labeled uncertain.

This is best-effort for sequential stale editors. A write between the fresh read and full `PUT`, from another backend instance or the importer, can still be lost. No local or backend-only lock solves that. A production guarantee requires upstream conditional writes or a single transactional write path respected by every writer.

## Two independent agent queues

The shared baseline already includes the dependency manifests, lockfiles, commit gate, and frozen API contract. One agent owns the backend queue; one owns the frontend queue. They begin from the same commit in separate worktrees. The backend agent touches only `backend/project_editor/` and `backend/tests/`. The frontend agent touches only `frontend/src/` and `frontend/vite.config.ts`. Neither agent owns shared documents, manifests, the other lane, or `upstream/`.

| Agent | Ordered tasks | Lane acceptance |
| --- | --- | --- |
| Backend | `T1.1` models; `T1.2` merge; `T1.3` adapter; `T1.4` routes | Ruff, ty, and backend tests pass |
| Frontend | `T2.1` Zod contract; `T2.2` relative API client; `T2.3` screen and proxy | TypeScript and Vite build pass |

The `blocked_by` edges stay within each queue. Backend and frontend work can start and finish independently; neither waits for a task in the other lane. Each task touches at most three files and has one acceptance command. Because the MVP already exists, agents compare each task with current code and make only needed changes. They report the commit and checks for their lane.

The integration owner merges both branches, checks the shared contract, runs the full pre-commit gate, and exercises the live list/show/save/conflict path and Vite proxy. That final check is outside both agent queues. Contract or dependency changes go through the integration owner before either lane adopts them. Search, pagination, authentication, a database, linked-company editing, and visual polish remain outside this MVP.
