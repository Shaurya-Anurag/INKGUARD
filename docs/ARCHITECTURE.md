# INKGUARD Architecture

## Overview

INKGUARD is a pre-publication brand governance prototype. Its backend is a FastAPI application using SQLAlchemy and SQLite by default.

## High-level flow

1. A workspace is created.
2. Brand rules, approved facts and terminology are configured.
3. Reference documents and content submissions are uploaded.
4. The compliance evaluator analyses submitted text.
5. Findings are persisted with severity, explanation, suggestion and offsets.
6. Reviewers inspect findings and submit revisions.
7. Revised content is evaluated as a new audit.
8. A reviewer explicitly approves or requests changes.
9. Audit events and aggregate analytics provide traceability.

## Main components

- `main.py`: API routes, persistence models, document processing and compliance logic.
- `inkguard_tests/`: automated backend regression tests.
- `storage/`: local uploaded-document storage.
- `docs/`: project and backend documentation.

## Data model

Workspace, Document, BrandRule, ApprovedFact, Terminology, Audit, Finding, Revision, Approval and AuditEvent.

## Evaluation behaviour

The current evaluator uses deterministic heuristics. It checks configured terminology, rules, claims and product-specific numeric mismatches. Findings are advisory. A missing approved source is not proof that a claim is false. Human review remains necessary.

## Approval integrity

- Audits with open findings cannot be approved.
- Reviewers must explicitly disposition findings.
- Approved audits cannot be revised or re-evaluated.
- Re-evaluation creates a new audit record.

## Storage and configuration

- Database: `DATABASE_URL`
- Local document storage: `INKGUARD_STORAGE`
- Upload limit: `MAX_UPLOAD_MB`
- CORS: `CORS_ORIGINS`

Defaults and setup instructions are documented in the root README.

## Current limitations

There is no authentication, authorization, production tenant isolation, OCR, migration framework or production object-storage integration. The application is a hackathon prototype, not a production security boundary.


## Query efficiency

Audit-list related data is loaded in batches to avoid N+1 database round trips. Analytics are computed with database-side grouped aggregates rather than loading all historical rows into application memory. The health endpoint executes a lightweight database probe and reports unavailable dependencies with HTTP 503.

This is a query-path optimization, not a performance certification. Production latency still needs measurement under realistic data volume and deployment conditions.
