import pytest
from fastapi.testclient import TestClient
import main


@pytest.fixture
def client(tmp_path):
    test_engine = main.create_engine(
        f"sqlite:///{tmp_path / 'finding_lifecycle.db'}",
        connect_args={"check_same_thread": False},
    )
    main.SessionLocal.configure(bind=test_engine)
    main.Base.metadata.create_all(test_engine)
    with TestClient(main.app) as test_client:
        yield test_client
    main.Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def create_audit_with_findings(client):
    workspace = client.post(
        "/api/workspaces", json={"name": "Lifecycle Test"}
    ).json()

    with main.SessionLocal() as db:
        document = main.Document(
            workspace_id=workspace["id"],
            filename="lifecycle.txt",
            content_type="text/plain",
            storage_path="unused",
            extracted_text="Miracle cure. Guaranteed results. Clinically proven.",
            sha256="1" * 64,
            kind="submission",
        )
        db.add(document)
        db.flush()
        db.add_all([
            main.Terminology(
                workspace_id=workspace["id"],
                term="miracle cure",
                term_type="prohibited",
            ),
            main.Terminology(
                workspace_id=workspace["id"],
                term="guaranteed results",
                term_type="prohibited",
            ),
            main.Terminology(
                workspace_id=workspace["id"],
                term="clinically proven",
                term_type="prohibited",
            ),
        ])
        db.commit()
        document_id = document.id

    response = client.post(
        "/api/audits",
        json={"workspace_id": workspace["id"], "document_id": document_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_finding_status_transitions_persist_and_are_audited(client):
    audit = create_audit_with_findings(client)
    aid = audit["id"]
    findings = audit["findings"]
    assert len(findings) >= 3

    expected = {
        findings[0]["id"]: "resolved",
        findings[1]["id"]: "accepted",
        findings[2]["id"]: "dismissed",
    }

    for finding_id, status in expected.items():
        response = client.patch(
            f"/api/findings/{finding_id}", params={"status": status}
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"id": finding_id, "status": status}

    refreshed = client.get(f"/api/audits/{aid}")
    assert refreshed.status_code == 200
    actual = {f["id"]: f["status"] for f in refreshed.json()["findings"]}
    assert {fid: actual[fid] for fid in expected} == expected
    assert all(actual[fid] == "open" for fid in actual.keys() - expected.keys())

    events = client.get(f"/api/audits/{aid}/events")
    assert events.status_code == 200
    status_events = [
        event for event in events.json()
        if event["action"] == "finding.status_updated"
    ]
    assert len(status_events) == 3
    assert {event["details"]["status"] for event in status_events} == {
        "resolved", "accepted", "dismissed"
    }


def test_approval_requires_every_finding_to_be_non_open_and_locks_audit(client):
    audit = create_audit_with_findings(client)
    aid = audit["id"]
    findings = audit["findings"]

    # One unresolved finding must block approval.
    for finding in findings[:-1]:
        response = client.patch(
            f"/api/findings/{finding['id']}",
            params={"status": "accepted"},
        )
        assert response.status_code == 200

    blocked = client.post(
        f"/api/audits/{aid}/approve",
        json={"decision": "approved", "reviewer": "Test Reviewer"},
    )
    assert blocked.status_code == 409
    assert "1 finding(s) are still open" in blocked.json()["detail"]

    # Dismissing the final finding closes the review queue.
    final_status = client.patch(
        f"/api/findings/{findings[-1]['id']}",
        params={"status": "dismissed"},
    )
    assert final_status.status_code == 200

    approved = client.post(
        f"/api/audits/{aid}/approve",
        json={
            "decision": "approved",
            "reviewer": "Test Reviewer",
            "comment": "All findings were dispositioned during the test.",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["decision"] == "approved"

    # Approved audits must be immutable.
    locked_status = client.patch(
        f"/api/findings/{findings[0]['id']}",
        params={"status": "open"},
    )
    locked_revision = client.post(
        f"/api/audits/{aid}/revisions",
        json={"content": "Attempted post-approval change."},
    )
    assert locked_status.status_code == 409
    assert locked_revision.status_code == 409

    persisted = client.get(f"/api/audits/{aid}").json()
    assert persisted["approval"]["decision"] == "approved"
    assert all(f["status"] != "open" for f in persisted["findings"])
