# Worktree ownership and integration

## Baseline and branches

The integrated MVP and approved `docs/sdd/` contract form the common baseline once committed. The task DAG describes a file-disjoint way to split further work; its pending statuses describe that proposed branch workflow, not the runtime state of this repository. Review the existing implementation and choose only tasks needed for the next change before opening worktrees. The current frontend is combined in `App.tsx` under one owner, as allowed by the architecture; splitting it is a future refactor if parallel view work is needed.

Create worktrees from the same baseline commit. Worktree names are suggestions; the ownership rule is the important part:

From the clean, committed integration branch, capture its commit and create only the worktrees needed for the next ready wave. For example, in PowerShell:

```powershell
$baselineCommit = git rev-parse HEAD
git worktree add -b feat/backend-merge ..\cms2-backend-merge $baselineCommit
git worktree add -b feat/backend-upstream ..\cms2-backend-upstream $baselineCommit
git worktree add -b feat/frontend-api ..\cms2-frontend-api $baselineCommit
```

For a fresh execution of the DAG, the five independent module tasks are eligible to run together after their model/schema dependencies. With three worker slots, run three first and schedule the other two as slots free up. For changes on this integrated baseline, select only relevant tasks and branch from the same commit. Branch names and paths must be unique.

| Lane | May edit | Must not edit |
| --- | --- | --- |
| `backend-contracts` | `backend/project_editor/contracts.py`, its focused tests | frontend, shared contract, root docs |
| `backend-merge` | `backend/project_editor/merge.py`, its focused tests | adapter, routes, frontend, shared contract |
| `backend-upstream` | `backend/project_editor/upstream.py`, its focused tests | merge, routes, frontend, shared contract |
| `frontend-data` | `frontend/src/contracts.ts`, `frontend/src/api.ts` | backend, screen components, shared contract |
| `frontend-view` | `frontend/src/ProjectList.tsx`, `ProjectForm.tsx`, `ConflictResolution.tsx` | API client, `App.tsx`, backend, shared contract |
| `integration` | `backend/project_editor/main.py`, `frontend/src/App.tsx`, `main.tsx`, `vite.config.ts`, root docs and gates | `upstream/` |

The task DAG can assign finer file-disjoint branches within a lane. Merge backend models before backend merge/adapter; merge frontend schemas before its API client or view components. Routes wait for backend merge and adapter. `App.tsx` waits for the frontend client and view parts. Backend routes and frontend assembly are independent and can run simultaneously. Cross-lane smoke checks wait for both.

No two workers own one file at the same time. If a contract change is needed, stop affected work, update `api-contract.md` in the integration lane, and rebase both lanes before continuing. Each lane returns a commit plus its focused acceptance output; the integration owner runs the full checks after merging.

Merge completed, file-disjoint branches into the integration branch after their acceptance checks. Build the routes from the merged backend models, merge, and adapter; build `App.tsx` from the merged frontend schemas, client, and views. Run the live backend/frontend check only after both assemblies merge. The integration owner alone changes root documents and shared contract files.
