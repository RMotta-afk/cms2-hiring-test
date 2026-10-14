# Worktree ownership and integration

## Baseline and branches

The committed MVP and [API contract](api-contract.md) are the shared baseline. Two agents work from the same integration commit in separate worktrees. The existing `feature-backend-worktree` and `feature-frontend-worktree` branches can be fast-forwarded from `main` while clean; future branches should also start from one common commit. Each agent first reads its queue and compares it with existing code, so completed behavior is verified or improved rather than blindly rebuilt.

| Agent | Task queue | May edit | Must not edit |
| --- | --- | --- | --- |
| Backend | `.context/tasks/backend/` | `backend/project_editor/`, `backend/tests/` | `frontend/`, `upstream/`, `docs/`, `.context/`, root files |
| Frontend | `.context/tasks/frontend/` | `frontend/src/`, `frontend/vite.config.ts` | `backend/`, `upstream/`, `docs/`, `.context/`, root files |
| Integration owner | Neither agent queue | Shared contract, plans, root documents, commit gate, final integration | `upstream/` |

Dependency manifests and lockfiles are part of the committed baseline. An agent requests a manifest or contract change from the integration owner before changing it. This keeps the two worktrees file-disjoint. The browser contract is frozen at `docs/sdd/api-contract.md`; both agents can work without waiting for the other's task status.

## Queue execution

The backend agent completes `T1.1` through `T1.4` in its worktree. The frontend agent completes `T2.1` through `T2.3` in its own worktree. A `blocked_by` edge may point only to an earlier task in the same agent's queue. There are no backend-to-frontend or frontend-to-backend task dependencies. Each queue ends with its own checks and a commit.

The task files are planning and tracking records. Their `pending` status does not mean the current MVP lacks that behavior; the agent reconciles each task against the existing implementation, makes only needed changes, and records the acceptance result in its task JSON. The frontend agent owns the combined `App.tsx` screen. Splitting that file into view components is optional within the frontend lane.

## Integration gate

After both agents report their commit and focused checks, the integration owner merges them into `main`. The owner checks for contract drift, runs Ruff, ty, backend tests, the frontend build, and the full pre-commit gate, then performs the live list/show/save/conflict and Vite proxy smoke check. Shared documentation is updated only by the integration owner. If either lane needs a contract change, the owner updates the SDD first and both agents base subsequent work on that revision.

A green lane check does not prove the two services work together. The live integration check is deliberately outside either agent queue; it starts after both branches are merged and does not block either agent's independent work.
