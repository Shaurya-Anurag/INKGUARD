from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import main


def test_upload_limit_is_enforced_while_streaming(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    main.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main, "STORAGE", tmp_path)
    monkeypatch.setattr(main, "MAX_UPLOAD_MB", 1)
    main.app.dependency_overrides[main.db_session] = override_db
    try:
        with TestClient(main.app) as client:
            workspace = client.post("/api/workspaces", json={"name": "VELORA"})
            assert workspace.status_code == 201
            wid = workspace.json()["id"]

            response = client.post(
                f"/api/documents/upload?workspace_id={wid}&kind=submission",
                files={"file": ("oversized.txt", b"x" * (1024 * 1024 + 1), "text/plain")},
            )
            assert response.status_code == 413
            assert list(tmp_path.iterdir()) == []
    finally:
        main.app.dependency_overrides.pop(main.db_session, None)
        engine.dispose()
