# Project editor implementation plan

Status: the shared-workspace MVP has been implemented against this contract. The task DAG remains a proposed file-disjoint worktree sequence, not a claim that the current code is absent. Its pending task statuses track that future branch workflow. Review existing code before assigning a task so work is not repeated.

This document is the human entry point. The normative architecture, allowed dependencies, API payloads, and worktree ownership live in [the SDD](sdd/architecture.md), [API contract](sdd/api-contract.md), and [worktree rules](sdd/worktrees.md). The machine-readable task DAG is in [`.context/decomposition.json`](../.context/decomposition.json), with one task file under `.context/tasks/` for each atomic task.

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

## Dependencies and parallel execution

The build uses Python 3.11+, FastAPI/Pydantic, HTTPX, Uvicorn, uv, pytest, Ruff, and ty on the backend; React, MUI, Zod, TypeScript, Vite, Node, and npm on the frontend; and pre-commit for the local gate. The manifests and lockfiles belong to the shared baseline, not to feature branches. The SDD fixes the exact responsibilities and file paths.

| Wave | Gate | Work that can proceed together |
| --- | --- | --- |
| 1. Shared baseline | Freeze and commit the SDD contract, manifests, lockfiles, buildable frontend placeholder, and hook config | Backend and frontend manifests are file-disjoint; frontend scaffold follows its manifest |
| 2. Typed contracts | Baseline is common to all worktrees | Pydantic backend models and Zod frontend schemas |
| 3. Independent modules | Relevant model/schema task has merged | Backend merge logic; upstream adapter; frontend API client; list view; form/conflict view |
| 4. Assembly | Each lane's modules have merged | Backend routes/tests and frontend screen/proxy, in separate worktrees |
| 5. Integration | Both assembled lanes have merged | Live smoke/decision record and run instructions; AI trail after checks |

The DAG encodes the exact `blocked_by` edges. A task may start as soon as its prerequisites have merged; workers need not wait for unrelated tasks in the same wave. Each task touches at most three files and has one acceptance check. The current Codex team can run three worker agents alongside the integration owner; the file-disjoint graph also works with more independent worktrees if available.

The integration owner controls `docs/sdd/`, `.context/`, root Markdown deliverables, and `.pre-commit-config.yaml`. Backend workers control only their assigned `backend/` files; frontend workers control only their assigned `frontend/` files. Component files are separate so list, form/conflict, and API-client work can be merged without competing edits to `App.tsx`. Only the frontend assembly task owns `App.tsx`. Only the backend route task owns `main.py`. A contract change goes through the integration owner and both lanes rebase before continuing.

Within the strict one-hour build, spend the time on a working list/show/save path, merge/conflict behavior, and honest verification. Search, pagination, authentication, a database, linked-company editing, and visual polish stay out of scope. The exact safety limit across three backend instances and the direct importer is documented above and in the SDD.
