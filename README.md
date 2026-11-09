# INKGUARD

INKGUARD is a pre-publication brand-governance workspace. Teams configure brand rules, approved product facts and terminology; submit content; inspect evidence-backed findings; revise; re-evaluate; and record a human approval decision.

> Automated findings are advisory. INKGUARD does not establish legal truth or automatically approve content. Human review is required.

## Product workflow

1. Open the VELORA workspace.
2. Configure verified brand rules, approved facts and prohibited/preferred terminology.
3. Upload a submission (PDF, DOCX, TXT, MD, CSV or JSON; 15 MB default limit).
4. Review the audit findings, explanations, suggestions and evidence.
5. Update finding dispositions or revise the content in Correction Studio.
6. Re-evaluate the revision. A new audit is created; the earlier audit remains in history.
7. Record an approval or request changes. Approval is blocked while any finding remains open.

## Stack

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4.
- **Backend:** FastAPI, SQLAlchemy.
- **Database:** SQLite by default; PostgreSQL can be configured with a SQLAlchemy URL.
- **Document extraction:** pypdf and python-docx; scanned-PDF OCR is not included.

## Run locally (Windows / Git Bash)

### 1. Backend

From the repository root:

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install -r requirements-dev.txt
uvicorn main:app --reload
```

Backend API: http://127.0.0.1:8000  
Interactive API docs: http://127.0.0.1:8000/docs  
Health check: http://127.0.0.1:8000/api/health

### 2. Frontend

Open a second terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Frontend: http://localhost:3000

The frontend expects the backend at `http://127.0.0.1:8000` by default. Change `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` if needed.

## Validation

Backend tests (repository root):

```bash
python -m pytest -q
```

Frontend checks (from `frontend/`):

```bash
npm run lint
npm run build
```

GitHub Actions runs backend tests and frontend lint/build on pushes to `main`, `backend-dev`, and `frontend-dev`, and on pull requests targeting `main`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./inkguard.db` | SQLAlchemy database URL |
| `INKGUARD_STORAGE` | `./storage` | Local upload storage directory |
| `MAX_UPLOAD_MB` | `15` | Maximum upload size |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed browser origins |

For PostgreSQL, install `psycopg[binary]` and set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL.

## API overview

- Workspaces: `GET/POST /api/workspaces`
- Documents: `POST /api/documents/upload`, `GET /api/documents`
- Brand rules: `GET/POST /api/brand/rules`, `PUT/DELETE /api/brand/rules/{id}`
- Approved facts: `GET/POST /api/brand/facts`, `PUT/DELETE /api/brand/facts/{id}`
- Terminology: `GET/POST /api/brand/terminology`, `PUT/DELETE /api/brand/terminology/{id}`
- Audits: `POST /api/audits`, `GET /api/audits`, `GET /api/audits/{id}`
- Revisions: `POST /api/audits/{id}/revisions`, `POST /api/audits/{id}/reevaluate`
- Review: `PATCH /api/findings/{id}`, `POST /api/audits/{id}/approve`
- History and analytics: `GET /api/events`, `GET /api/audits/{id}/events`, `GET /api/analytics/overview`

The running app's `/openapi.json` is the source of truth for request and response schemas.

## Known prototype limitations

- No authentication, authorization, or production tenant isolation. Do not expose this API publicly or use it with sensitive customer content.
- Evaluation is deterministic and heuristic. No LLM/RAG engine is implemented.
- No OCR for scanned PDFs.
- Claim and numeric matching can produce false positives and false negatives.
- Compliance score is a transparent demo heuristic, not a legal or regulatory certification.
- SQLite schema creation uses `create_all`; production migrations are not configured.
- Local file storage is used by default; production object storage, retention and backup controls are not configured.
- No load or concurrency certification.

## Project structure

- `main.py` — API, persistence models, document extraction and evaluator.
- `inkguard_tests/` — backend regression and workflow tests.
- `frontend/` — Next.js application and typed API client.
- `docs/` — API and architecture notes.


## Query efficiency

Audit lists now load approval decisions and finding counts in batched queries rather than issuing per-audit lookups. Workspace analytics use database-side aggregates instead of loading every audit, finding and approval into application memory. The health endpoint performs a lightweight database connectivity check and returns HTTP 503 when the database cannot be reached.

These changes reduce avoidable database round trips and application memory use; they do not replace production load testing or resolve latency caused by serverless cold starts, network distance, or external infrastructure.
