# INKGUARD

AI-assisted brand governance and pre-publication content review. This repository currently contains a **prototype backend** built with FastAPI, SQLAlchemy, and SQLite by default.

> Automated findings are advisory. INKGUARD does not establish legal truth or automatically approve content. Human review is required.

## Backend setup (Windows / Git Bash)

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation and `http://127.0.0.1:8000/api/health` for the health check.

## Tests

```bash
python -m pytest -q
```

The tests cover the VELORA compliance regression fixture, approval workflow rules, approved-audit immutability, and upload-size enforcement.

## Main workflow

1. Create a workspace.
2. Add verified brand rules, approved facts, and terminology.
3. Upload content using `kind=submission`.
4. Create an audit for that document.
5. Review findings and their evidence.
6. Add a revision and re-evaluate it to create a new audit.
7. Resolve, dismiss, or explicitly accept findings before approving.

## Important API routes

- `POST /api/workspaces`
- `POST /api/documents/upload`
- `POST /api/brand/rules`
- `POST /api/brand/facts`
- `POST /api/brand/terminology`
- `POST /api/audits`
- `GET /api/audits/{aid}`
- `POST /api/audits/{aid}/revisions`
- `POST /api/audits/{aid}/reevaluate`
- `PATCH /api/findings/{fid}?status=resolved`
- `POST /api/audits/{aid}/approve`
- `GET /api/analytics/overview`

## Configuration

- `DATABASE_URL`: defaults to `sqlite:///./inkguard.db`.
- `INKGUARD_STORAGE`: defaults to `./storage`.
- `MAX_UPLOAD_MB`: defaults to `15`.
- `CORS_ORIGINS`: comma-separated origins; defaults to localhost ports used by Next.js.

For PostgreSQL, install `psycopg[binary]` and set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL.

## Prototype limitations — do not misrepresent these

- No authentication, authorization, or tenant isolation. Do not expose this API publicly.
- Compliance evaluation is deterministic and heuristic; no LLM/RAG engine is implemented.
- No OCR for scanned PDFs.
- Numeric matching and claim detection can produce false positives/negatives.
- SQLite schema creation uses `create_all`; production migrations are not configured.
- Local file storage is used by default; production object storage and retention controls are not configured.
- Compliance score is a transparent demo heuristic, not a legal or regulatory certification.
