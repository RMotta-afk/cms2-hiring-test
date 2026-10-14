# Project editor

A small React and FastAPI editor for the fictional upstream records API. It lists projects, shows one project, and saves edits to its core fields and key dates. The browser uses only this backend's `/api` routes; the upstream API key stays on the backend.

## Run locally

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), Node, and npm. Start each command in a separate terminal from the repository root:

```sh
cd upstream
uv run upstream
```

```sh
cd backend
uv run project-editor
```

```sh
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The backend is at `http://127.0.0.1:8080`; Vite proxies `/api` to it. The backend defaults to `http://127.0.0.1:8081` and the starter's local API key. Set `UPSTREAM_URL` and `UPSTREAM_API_KEY` in the backend process when using another upstream. Do not put the key in frontend environment variables.

The upstream intentionally has a roughly 10% chance of a slow individual read or an ambiguous `504` on save. To make local checks deterministic, set `UPSTREAM_SLOW_RATE=0` and `UPSTREAM_TIMEOUT_RATE=0` **in the upstream process** before starting it. Its records live in memory and reset on restart.

## API contract

| Route | Success | Other relevant responses |
| --- | --- | --- |
| `GET /api/projects` | `{ "projects": [{ "id", "name", "sector", "country", "stage" }] }` | `502` upstream unavailable |
| `GET /api/projects/{id}` | `{ "project": { "id", "name", "sector", "country", "stage", "key_dates" } }` | `404`, `502` |
| `PUT /api/projects/{id}` | `{ "project": ... }` | `409` edit conflict, `504` uncertain write, `422` invalid request |

The `PUT` body is `{ "base": EditableFields, "proposed": EditableFields }`. `EditableFields` contains `name`, `sector`, `country`, `stage`, and `key_dates: [{ "label", "date" }]`; dates are `YYYY-MM-DD`. Both snapshots are required so the backend can identify what the editor actually changed. `409` returns `{ "code": "edit_conflict", "current": ProjectDetail, "conflicting_fields": [...] }`. `504` returns `{ "code": "write_uncertain", "observed": ProjectDetail | null }`. The frontend parses these contracts with Zod; the backend validates them with Pydantic.

On conflict, choose current or mine for each overlapping field and resubmit against the returned current record. The entire key-date list is one field. The UI supports adding, editing, and removing date rows. `linked_companies` is not exposed for editing, but the backend includes its latest read value in the upstream's required full `PUT`.

## Check the project

```sh
pre-commit install
pre-commit run --all-files
cd backend && uv run pytest -q && uv run ty check project_editor tests
cd ../frontend && npm run build
```

The installed commit hook runs file checks, Ruff lint and format, backend ty and tests, and the frontend build for relevant staged files. It does not touch `upstream/`. Ruff is pinned to `0.16.10` in the hook and backend project; `uvx ruff@0.16.10` invokes the same version directly.

## Limits

This is a focused editor, not a production concurrency guarantee. The upstream has no revision or conditional write, and an importer writes to it directly. Two writers can change it between this backend's fresh read and full `PUT`. A timed-out write may have happened; the editor re-reads when possible, reports what it observed, and does not retry automatically. See [DECISIONS.md](DECISIONS.md) for the exact tradeoffs and [AI_TRAIL.md](AI_TRAIL.md) for the development approach.
