# Project guidance

## Purpose and scope

Build the smallest honest, interview-ready project editor. Keep the code easy to explain and change live. Prefer one complete list/show/save path over broad scaffolding or UI polish. Do not publish the repository, invite collaborators, or contact BNamericas unless the user asks.

Read the [original challenge README](https://github.com/juandiegoantezana-zaga/cms2-hiring-starter/blob/main/README.md), `upstream/README.md`, `upstream/records_api/main.py`, and `upstream/tests/test_api.py` before changing upstream behavior. Do not modify `upstream/`.

## Required product slice

- The FastAPI backend lists projects, gets one project, and saves one project through the upstream API.
- The React and MUI frontend has one screen with a project list and a form for `name`, `sector`, `country`, `stage`, and `key_dates`.
- The browser calls only our backend. The backend owns the upstream API key.
- Two stale editors can save different fields without losing either change. An overlapping change is shown to the second editor, who chooses what to keep per field.
- Treat the whole `key_dates` list as one conflict field because entries have no stable IDs. Explain the extra conflicts this causes in `DECISIONS.md`.
- Keep `linked_companies` out of the form, but preserve its latest upstream value in the required full `PUT`.

## Upstream facts

- Local URL: `http://127.0.0.1:8081`. Start from `upstream/` with `uv run upstream`. Every request requires `X-Api-Key: local-dev-key`.
- `GET /projects` returns 30 full records; `GET /projects/{id}` returns one. Unknown IDs return `404`.
- `PUT /projects/{id}` requires `name`, `sector`, `country`, `stage`, `key_dates`, and `linked_companies`. Both lists are replaced wholesale.
- Sector values: `energy`, `mining`, `water`, `transport`, `oil_and_gas`, `ict`. Stage values: `idea`, `feasibility`, `tender`, `financing`, `construction`, `operation`, `cancelled`. Linked-company roles: `owner`, `developer`, `epc_contractor`, `financier`, `consultant`.
- Upstream has no revision, ETag, conditional write, or conflict detection. Last `PUT` wins.
- Some individual reads take about two seconds. Some saves return `504`; a timed-out save may have applied. Never claim a definite outcome or blindly retry it. `UPSTREAM_SLOW_RATE=0` and `UPSTREAM_TIMEOUT_RATE=0` make local checks deterministic.
- Upstream state is in memory and resets on restart. Production has three backend instances and a nightly importer that writes directly upstream. A read/merge/write flow cannot guarantee no lost update across all writers.

## Design, verification, and handoff

Keep upstream HTTP access, pure merge decisions, and UI state separate. Compare the form's original snapshot, proposed edits, and a fresh upstream record. Merge different-field changes and return a conflict for overlapping changes. If current already equals proposed, treat the field as resolved.

Check distinct-field saves, same-field conflicts, key-date conflicts, linked-company preservation, applied and unapplied `504` outcomes, and no direct browser call upstream. Run the app and state what was verified. Skip search, pagination, dashboards, authentication, a database, process-local locks, embedded AI, and elaborate styling unless the user changes scope.

Keep `README.md` human-facing with exact run commands, `DECISIONS.md` concise about trade-offs and safety limits, and `AI_TRAIL.md` honest about AI assistance and verification. Supporting design belongs under `docs/`. The user's current instruction is to leave `README.md` untouched.

For library or framework API details, use the current Context7 CLI workflow: resolve the official library name with `library`, then fetch `docs` with the returned ID. This does not apply to business-logic reasoning or code review.
