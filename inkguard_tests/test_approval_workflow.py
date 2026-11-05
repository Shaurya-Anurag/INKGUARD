import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main


def make_db():
    engine = create_engine("sqlite:///:memory:")
    main.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def seed_audit(db):
    workspace = main.Workspace(name="VELORA")
    db.add(workspace)
    db.flush()
    document = main.Document(
        workspace_id=workspace.id, filename="submission.txt", content_type="text/plain",
        storage_path="/tmp/submission.txt", extracted_text="Example", sha256="0" * 64,
        kind="submission",
    )
    db.add(document)
    db.flush()
    audit = main.Audit(workspace_id=workspace.id, document_id=document.id,
                       status="completed", score=50, summary="Test audit")
    db.add(audit)
    db.flush()
    finding = main.Finding(
        audit_id=audit.id, category="claims", finding_type="unsupported_claim",
        severity="high", status="open", detected_text="guaranteed results",
        explanation="Needs substantiation", suggestion="Qualify the claim",
        confidence=0.8, evidence=[],
    )
    db.add(finding)
    db.add(main.Approval(audit_id=audit.id))
    db.commit()
    return audit, finding


def test_approval_blocked_while_findings_are_open():
    db = make_db()
    try:
        audit, _ = seed_audit(db)
        payload = main.ApprovalIn(decision="approved", reviewer="Shaurya", comment="Attempted approval")
        with pytest.raises(HTTPException) as exc:
            main.approve(audit.id, payload, db)
        assert exc.value.status_code == 409
        assert "still open" in exc.value.detail
        approval = db.query(main.Approval).filter_by(audit_id=audit.id).one()
        assert approval.decision == "pending"
    finally:
        db.close()


def test_approval_allowed_after_finding_is_resolved():
    db = make_db()
    try:
        audit, finding = seed_audit(db)
        finding.status = "resolved"
        db.commit()
        result = main.approve(audit.id, main.ApprovalIn(decision="approved", reviewer="Shaurya"), db)
        assert result["decision"] == "approved"
    finally:
        db.close()


def test_approved_audit_findings_are_immutable():
    db = make_db()
    try:
        audit, finding = seed_audit(db)
        finding.status = "resolved"
        db.commit()
        main.approve(audit.id, main.ApprovalIn(decision="approved", reviewer="Shaurya"), db)
        with pytest.raises(HTTPException) as exc:
            main.set_finding_status(finding.id, "open", db=db)
        assert exc.value.status_code == 409
    finally:
        db.close()
