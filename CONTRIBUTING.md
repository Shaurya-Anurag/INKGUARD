# Contributing to INKGUARD

## Branching

- `main`: stable integration branch.
- `backend-dev`: backend development.
- `frontend-dev`: frontend development.
- Use short-lived feature branches when practical.

## Workflow

1. Sync your branch with its base branch.
2. Create a focused change.
3. Run relevant tests locally.
4. Open a pull request.
5. Review the diff and CI results before merging.

## Backend checks

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Pull requests

Include what changed and why, how it was tested, screenshots for UI changes, API or schema changes, and known limitations or follow-up work.

Do not commit secrets, local databases, virtual environments, uploaded customer documents or generated test output. Do not represent heuristic compliance findings as legal determinations.
