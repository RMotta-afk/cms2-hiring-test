# Software design: project editor

## Mission and scope

Build a small editor in front of the fixed records API. The usable path is list projects, show one, and save changes to core fields and key dates. Sequential stale editors must retain nonoverlapping changes and receive an explicit choice for overlapping changes. The browser uses only the editor backend. The application must be easy to extend live.

`upstream/` is owned by another team and is read-only. This project does not add a database, authentication, search, pagination, linked-company editing, or a distributed lock. The upstream offers no conditional write; the design documents the remaining read/write race across three backend instances and the direct importer.

## Allowed components and files

| Component | Responsibility | Owned paths |
| --- | --- | --- |
| Shared contract | Normative browser API and cross-worktree decisions | `docs/sdd/api-contract.md`, `docs/sdd/architecture.md`, `docs/sdd/worktrees.md` |
| Shared scaffold | Reproducible manifests and a buildable placeholder frontend before parallel work | `backend/project_editor/__init__.py`, `frontend/index.html`, `frontend/tsconfig.json`, `frontend/src/main.tsx` |
| Backend models | Validate browser input and parse the wide upstream record; expose only small response models | `backend/project_editor/contracts.py` |
| Merge domain | Pure per-field three-way merge; atomic `key_dates` conflict | `backend/project_editor/merge.py` |
| Upstream adapter | Authenticate, list/get/full-PUT, map transport and ambiguous-write failures | `backend/project_editor/upstream.py` |
| Backend routes | Implement only the three `/api/projects` routes and their response codes | `backend/project_editor/main.py` |
| Backend checks | Focused behavior and adapter tests | `backend/tests/` |
| Frontend schemas | Zod versions of the browser contract | `frontend/src/contracts.ts` |
| Frontend client | Relative `/api` requests and response parsing | `frontend/src/api.ts` |
| Frontend screen | List, edit form, per-field conflict choice, save/rebase state, and uncertainty handling | `frontend/src/App.tsx` |
| Frontend delivery | Entry point and local backend proxy | `frontend/src/main.tsx`, `frontend/vite.config.ts` |
| Handoff | Human setup instructions, tradeoffs, and AI trail | `README.md`, `DECISIONS.md`, `AI_TRAIL.md` |

One frontend agent owns the complete frontend lane, including the combined `App.tsx` screen. One backend agent owns the backend lane. Neither agent edits shared contracts, root documents, or the other lane's files. The shared API contract remains authoritative if code and prose disagree during parallel work.

## Backend module interfaces

`contracts.py` owns `EditableFields`, `ProjectDetail`, `ProjectSummary`, `StoredProject`, the exact sector/stage literals, and the request/error response models in `api-contract.md`. `StoredProject` retains `linked_companies` for upstream writes but its browser projection omits it.

`merge.py` exports `merge_edit(base: EditableFields, proposed: EditableFields, current: EditableFields) -> MergeResult`. `MergeResult` contains `merged: EditableFields`, `conflicts: list[EditableFieldName]`, and `changed: bool` (whether the merged editable values differ from current). It has no HTTP or FastAPI imports.

`upstream.py` exports a `ProjectStore` interface with `list_projects() -> list[StoredProject]`, `get_project(id) -> StoredProject`, and `put_project(id, fields: EditableFields, linked_companies: list[LinkedCompany]) -> StoredProject`, all asynchronous. It signals missing projects, unavailable reads, and uncertain writes distinctly. `main.py` alone maps those outcomes to the browser HTTP responses. No worker adds a fourth endpoint.

## Frontend component interfaces

`contracts.ts` exports Zod schemas and inferred `ProjectSummary`, `ProjectDetail`, `EditableFields`, and `EditableField` types. `api.ts` exports `listProjects()`, `getProject(id)`, and `saveProject(id, base, proposed)`; save returns a discriminated result for `saved`, `conflict`, or `uncertain`. It alone calls `fetch`, always with relative `/api` paths.

`App.tsx` owns selection, the list and edit form, base/draft snapshots, key-date rows, per-field conflict choices, conflict rebase, uncertainty, and API orchestration. It calls the frontend API client, never the upstream. The frontend agent may later extract view components within its own lane without changing the browser contract.

## Allowed dependencies

| Area | Runtime | Development/checking | Manifest |
| --- | --- | --- | --- |
| Backend | Python 3.11+, FastAPI/Pydantic, HTTPX, Uvicorn | uv, pytest, Ruff, ty | `backend/pyproject.toml`, `backend/uv.lock` |
| Frontend | React, MUI, Zod | TypeScript, Vite, npm | `frontend/package.json`, `frontend/package-lock.json` |
| Commit gate | pre-commit, Ruff hook, local ty/test/build hooks | pre-commit | `.pre-commit-config.yaml` |

The backend owns the upstream API key through its process environment. The frontend must never embed it or address the upstream origin. Vite proxies relative `/api` requests to the backend for local development. A production host must route that same path to the backend.

## Runtime behavior and safety

The upstream `GET /projects` returns full records; the backend narrows them for the browser. A save fetches the latest project, runs the merge described in `api-contract.md`, and sends the upstream's required full `PUT` only when conflict-free and changed. The full body includes the latest observed `linked_companies`. A `504` or lost PUT response is uncertain; one diagnostic read is allowed, but automatic retry is not.

The three-way merge handles sequential stale editors. It cannot close the gap between its fresh read and upstream `PUT`. Another backend instance or the nightly importer may write in that gap. A strict no-lost-update guarantee requires upstream revision/conditional writes or one transactional write path used by every writer. Neither is in this implementation.
