# INKGUARD backend session notes — 5 November

## Changes in this patch
- Approval returns HTTP 409 if any finding remains `open`.
- `accepted`, `dismissed`, and `resolved` are explicit reviewer dispositions and do not block approval.
- Findings on an approved audit are immutable; create a new revision/audit to change reviewed content.
- Uploads are streamed to disk in chunks; the configured size limit is enforced before accepting excess bytes.
- Added regression tests for approval gating, approved-audit immutability, and upload limits.

## Run tests
```bash
python -m pytest -q
```

## Remaining priorities
1. Add endpoint tests for workspace/document isolation and invalid uploads.
2. Add authentication/authorization before any public deployment.
3. Add robust document retention/deletion and production object storage.
4. Split the prototype into routers/services/models after API contracts are agreed with frontend.
5. Add database migrations before moving beyond SQLite prototype use.

## Finding status semantics
- `open`: unresolved; blocks approval.
- `accepted`: reviewer explicitly accepts the flagged risk.
- `dismissed`: reviewer determines the finding does not apply.
- `resolved`: content has been corrected.
