# AI trail

## Before code

I read the challenge PDF, starter README, upstream README, implementation, tests, and local `AGENTS.md`. I chose a strict one-hour scope: list, show, and save a record with honest concurrent-edit and timeout behavior. The upstream's full-replacement `PUT`, missing revision, ambiguous `504`, three backend instances, and direct importer shaped the design before feature coding. I established a pre-commit gate first, with pinned Ruff, file checks, ty, backend tests, and a frontend build. Current library tooling details were checked through Context7 CLI documentation.

## What AI produced and what I directed

Codex implemented the FastAPI contract, upstream adapter, pure merge function, focused tests, and documentation. A parallel frontend subagent implemented the React/MUI screen and Zod API schemas under `frontend/` against an agreed endpoint contract. I set the request and response shapes before parallel work and confirmed two product decisions with the user: date rows support add/edit/remove, and conflicts are resolved per field with the whole date list treated as one field. The root `AGENTS.md` records the task guidance supplied to the tooling.

## Oversight and checks

I reviewed the frontend payloads against the backend models, corrected the Vite proxy target through the frontend agent, and asked it to remove broken punctuation in UI strings. I used the upstream tests to verify its awkward behavior rather than changing upstream code. This backend lane added pure merge and HTTP adapter tests; the backend suite now has 17 passing tests. Ruff, ty, the frontend build, and the pre-commit gate also passed. With the actual upstream and backend running, I checked the list, show, nonoverlapping saves, and an overlapping conflict; the Vite proxy also returned the project list. Applied and unapplied `504` outcomes were exercised by deterministic backend tests. No browser UI automation was available in this environment, so I have not claimed a manual UI pass.

The native Codex conversation is the source transcript for prompts, tool calls, decisions, and test output. This file summarizes it without inventing exchanges or including credentials.
