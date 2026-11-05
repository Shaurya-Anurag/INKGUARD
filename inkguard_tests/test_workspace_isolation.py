from fastapi.testclient import TestClient
import main


def test_brand_sources_and_audits_reject_cross_workspace_documents(tmp_path):
    engine = main.create_engine(
        f"sqlite:///{tmp_path / 'isolation.db'}",
        connect_args={"check_same_thread": False}
    )
    main.SessionLocal.configure(bind=engine)
    main.Base.metadata.create_all(engine)
    try:
        with TestClient(main.app) as client:
            a = client.post("/api/workspaces", json={"name": "Workspace A"}).json()
            b = client.post("/api/workspaces", json={"name": "Workspace B"}).json()
            with main.SessionLocal() as db:
                doc = main.Document(
                    workspace_id=a["id"], filename="source.txt", content_type="text/plain",
                    storage_path="unused", extracted_text="Approved source text.",
                    sha256="a"*64, kind="submission"
                )
                db.add(doc); db.commit(); db.refresh(doc)
                doc_id = doc.id

            rule = client.post("/api/brand/rules", json={
                "workspace_id": b["id"], "title": "Rule", "description": "avoid: risky",
                "source_document_id": doc_id
            })
            fact = client.post("/api/brand/facts", json={
                "workspace_id": b["id"], "subject": "Product", "attribute": "concentration",
                "approved_value": "10", "source_document_id": doc_id
            })
            audit = client.post("/api/audits", json={
                "workspace_id": b["id"], "document_id": doc_id
            })

            assert rule.status_code == 400
            assert fact.status_code == 400
            assert audit.status_code == 404
    finally:
        main.Base.metadata.drop_all(engine)
        engine.dispose()
