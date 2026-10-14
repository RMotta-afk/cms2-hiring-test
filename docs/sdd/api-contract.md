# Browser API contract

This is the frozen contract for separate backend and frontend worktrees. Contract changes belong to the integration owner and require both lanes to update their validation and tests together.

## Types

```text
Sector = energy | mining | water | transport | oil_and_gas | ict
Stage = idea | feasibility | tender | financing | construction | operation | cancelled
KeyDate = { label: nonblank string, date: valid ISO calendar date YYYY-MM-DD }
EditableFields = { name: nonblank string, sector: Sector, country: nonblank string,
                   stage: Stage, key_dates: KeyDate[] }
ProjectSummary = { id: string, name: string, sector: Sector, country: string, stage: Stage }
ProjectDetail = { id: string, ...EditableFields }
EditableFieldName = name | sector | country | stage | key_dates
```

Request bodies require their declared fields and reject extras. The backend does not silently trim the original snapshot, since exact comparison is needed for conflict detection. The UI may validate a draft's visible text but must keep the base snapshot as received. Date entries have no stable IDs, so the whole `key_dates` array is one conflict field.

## Endpoints

| Method | Path | Request | `200` response |
| --- | --- | --- | --- |
| GET | `/api/projects` | none | `{ "projects": ProjectSummary[] }` |
| GET | `/api/projects/{id}` | none | `{ "project": ProjectDetail }` |
| PUT | `/api/projects/{id}` | `{ "base": EditableFields, "proposed": EditableFields }` | `{ "project": ProjectDetail }` |

No browser-facing route exposes `linked_companies` or other read-only upstream fields. The backend includes `linked_companies` from the latest read when it sends the upstream's full `PUT`.

## Error responses

| Status | JSON body | Client action |
| --- | --- | --- |
| `404` | `{ "code": "project_not_found" }` | Show missing record |
| `409` | `{ "code": "edit_conflict", "current": ProjectDetail, "conflicting_fields": EditableFieldName[] }` | Choose current or mine separately for each named field, then rebase and resubmit |
| `422` | FastAPI validation error | Correct invalid input |
| `502` | `{ "code": "upstream_unavailable" }` | Keep the draft and allow a later read retry |
| `504` | `{ "code": "write_uncertain", "observed": ProjectDetail | null }` | Do not retry automatically; show what a diagnostic read observed and ask the editor to review |

The frontend must parse successful and named error bodies with Zod. Other HTTP failures may use a generic message while preserving the unsaved draft. The backend must not report a timed-out save as a definite failure or success.

## Merge contract

The server compares `base`, `proposed`, and a fresh upstream `current` value for each of the five editable fields:

| Condition | Result |
| --- | --- |
| `proposed == base` | Keep `current` |
| `current == base` | Use `proposed` |
| `current == proposed` | Keep `current`; the requested value is already present |
| Otherwise | Add the field to `conflicting_fields` |

If any field conflicts, return `409` without a `PUT`. Otherwise send a full upstream body with the merged fields and the latest read `linked_companies`. If the merged editable fields already equal `current`, return the current project without a `PUT`. A `504` or lost PUT response triggers at most one diagnostic read, never an automatic write retry.

After `409`, the client constructs a new base from `current`, reapplies its nonconflicting draft changes, applies the editor's choices to conflicting fields, and submits again. If the record changed again, another `409` is valid.
