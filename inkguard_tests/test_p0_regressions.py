import pytest
from fastapi.testclient import TestClient
import main


@pytest.fixture
def client(tmp_path):
    test_engine = main.create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False}
    )
    main.SessionLocal.configure(bind=test_engine)
    main.Base.metadata.create_all(test_engine)
    with TestClient(main.app) as c:
        yield c
    main.Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def make_audit(client, text="A simple approved draft."):
    ws = client.post("/api/workspaces", json={"name": "VELORA"}).json()
    with main.SessionLocal() as db:
        doc = main.Document(
            workspace_id=ws["id"], filename="submission.txt", content_type="text/plain",
            storage_path="unused", extracted_text=text, sha256="0"*64, kind="submission"
        )
        db.add(doc); db.commit(); db.refresh(doc)
        doc_id = doc.id
    response = client.post("/api/audits", json={"workspace_id": ws["id"], "document_id": doc_id})
    assert response.status_code == 201, response.text
    return ws, response.json()


def test_approved_audit_rejects_revision_and_reevaluation(client):
    _, audit = make_audit(client)
    aid = audit["id"]
    approved = client.post(f"/api/audits/{aid}/approve", json={"decision": "approved"})
    assert approved.status_code == 200
    revision = client.post(f"/api/audits/{aid}/revisions", json={"content": "Changed after approval."})
    reevaluate = client.post(f"/api/audits/{aid}/reevaluate")
    assert revision.status_code == 409
    assert reevaluate.status_code == 409


def test_preferred_terminology_is_low_severity_recommendation(client):
    ws, _ = make_audit(client, "Our product is a moisturizer.")
    response = client.post("/api/brand/terminology", json={
        "workspace_id": ws["id"], "term": "moisturizer",
        "replacement": "hydrating cream", "term_type": "preferred"
    })
    assert response.status_code == 201
    with main.SessionLocal() as db:
        findings = main.evaluate(db, ws["id"], "Our product is a moisturizer.")
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "preferred_term_recommendation"
    assert findings[0]["severity"] == "low"
    assert "not a compliance violation" in findings[0]["explanation"]


def test_numeric_fact_requires_matching_product_subject(client):
    ws, _ = make_audit(client)
    with main.SessionLocal() as db:
        db.add(main.ApprovedFact(
            workspace_id=ws["id"], subject="VELORA Vitamin C Serum",
            attribute="Vitamin C concentration", approved_value="10", unit="%", verified=True
        ))
        db.commit()
        matching = main.evaluate(db, ws["id"], "VELORA Vitamin C Serum\nOur formula contains 20% Vitamin C.")
        unrelated = main.evaluate(db, ws["id"], "LUMI Niacinamide Serum\nOur formula contains 20% Vitamin C.")
    assert any(x["finding_type"] == "fact_contradiction" for x in matching)
    assert not any(x["finding_type"] == "fact_contradiction" for x in unrelated)
