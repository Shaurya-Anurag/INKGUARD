# INKGUARD API Reference

Interactive OpenAPI documentation is available at `/docs`. The OpenAPI schema is available at `/openapi.json`.

All routes use the `/api` prefix unless stated otherwise.

## Health

- `GET /api/health`

## Workspaces

- `POST /api/workspaces`
- `GET /api/workspaces`
- `GET /api/workspaces/{wid}`

## Documents

- `POST /api/documents/upload` — query: `workspace_id` (required), `kind` (optional); multipart field: `file`.
- `GET /api/documents?workspace_id={id}`
- `GET /api/documents/{did}`

## Brand configuration

- `POST /api/brand/rules`
- `GET /api/brand/rules?workspace_id={id}`
- `POST /api/brand/facts`
- `GET /api/brand/facts?workspace_id={id}`
- `POST /api/brand/terminology`
- `GET /api/brand/terminology?workspace_id={id}`

## Audits and review

- `POST /api/audits`
- `GET /api/audits?workspace_id={id}`
- `GET /api/audits/{aid}`
- `POST /api/audits/{aid}/revisions`
- `POST /api/audits/{aid}/reevaluate`
- `POST /api/audits/{aid}/approve`
- `PATCH /api/findings/{fid}?status={status}`

## Events and analytics

- `GET /api/audits/{aid}/events`
- `GET /api/events?workspace_id={id}&limit=50`
- `GET /api/analytics/overview?workspace_id={id}`

## Important behaviour

- Approval is rejected while findings remain open.
- Findings require explicit reviewer disposition.
- Re-evaluation creates a new audit.
- Approved audits reject further revisions and re-evaluation.
- Automated findings are advisory and require human review.

For exact request and response schemas, use the running application's `/openapi.json`.
