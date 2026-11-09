from fastapi.testclient import TestClient
import main


def test_health_checks_database_connectivity():
    with TestClient(main.app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_audit_list_and_analytics_preserve_aggregate_contract(tmp_path):
    engine = main.create_engine(
        f"sqlite:///{tmp_path / 'query_efficiency.db'}",
        connect_args={"check_same_thread": False},
    )
    main.SessionLocal.configure(bind=engine)
    main.Base.metadata.create_all(engine)
    try:
        with TestClient(main.app) as client:
            workspace = client.post(
                "/api/workspaces", json={"name": "Query Test"}
            ).json()
            with main.SessionLocal() as db:
                document = main.Document(
                    workspace_id=workspace["id"],
                    filename="submission.txt",
                    content_type="text/plain",
                    storage_path="unused",
                    extracted_text="A claim that is 100% safe.",
                    sha256="a" * 64,
                    kind="submission",
                )
                db.add(document)
                db.commit()
                db.refresh(document)
                audit = main.run_audit(
                    db, workspace["id"], document, document.extracted_text
                )
                audit_id = audit.id

            audit_list = client.get(
                "/api/audits", params={"workspace_id": workspace["id"]}
            )
            assert audit_list.status_code == 200
            assert len(audit_list.json()) == 1
            assert audit_list.json()[0]["id"] == audit_id
            assert audit_list.json()[0]["finding_count"] == 1
            assert audit_list.json()[0]["approval_decision"] == "pending"

            analytics = client.get(
                "/api/analytics/overview",
                params={"workspace_id": workspace["id"]},
            )
            assert analytics.status_code == 200
            body = analytics.json()
            assert body["total_audits"] == 1
            assert body["total_findings"] == 1
            assert body["open_findings"] == 1
            assert body["severity_breakdown"]["high"] == 1
            assert body["approved_audits"] == 0
            assert body["changes_requested"] == 0
    finally:
        main.Base.metadata.drop_all(engine)
        engine.dispose()
