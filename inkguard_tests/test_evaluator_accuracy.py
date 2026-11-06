import pytest
import main


@pytest.fixture
def db_session(tmp_path):
    engine = main.create_engine(
        f"sqlite:///{tmp_path / 'evaluator_accuracy.db'}",
        connect_args={"check_same_thread": False},
    )
    main.SessionLocal.configure(bind=engine)
    main.Base.metadata.create_all(engine)
    with main.SessionLocal() as db:
        yield db
    main.Base.metadata.drop_all(engine)
    engine.dispose()


def add_term(db, workspace_id, term, case_sensitive=False):
    item = main.Terminology(
        workspace_id=workspace_id,
        term=term,
        term_type="prohibited",
        case_sensitive=case_sensitive,
    )
    db.add(item)
    db.commit()
    return item


def test_prohibited_terminology_matches_whole_terms_not_substrings(db_session):
    workspace = main.Workspace(name="Boundary Test")
    db_session.add(workspace)
    db_session.commit()
    add_term(db_session, workspace.id, "safe")

    findings = main.evaluate(
        db_session,
        workspace.id,
        "This formula is unsafe, but the word safe appears separately.",
    )
    assert len(findings) == 1
    assert findings[0]["detected_text"] == "safe"


def test_prohibited_phrase_does_not_duplicate_contained_claim_flag(db_session):
    workspace = main.Workspace(name="Overlap Test")
    db_session.add(workspace)
    db_session.commit()
    add_term(db_session, workspace.id, "miracle cure")

    findings = main.evaluate(
        db_session,
        workspace.id,
        "This is a miracle cure for damaged skin.",
    )
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "terminology_violation"
    assert findings[0]["detected_text"] == "miracle cure"


def test_case_sensitive_terminology_respects_configured_case(db_session):
    workspace = main.Workspace(name="Case Test")
    db_session.add(workspace)
    db_session.commit()
    add_term(db_session, workspace.id, "Miracle Cure", case_sensitive=True)

    findings = main.evaluate(
        db_session,
        workspace.id,
        "miracle cure is claimed here. MIRACLE CURE is also claimed. Miracle Cure appears exactly.",
    )
    assert len(findings) == 1
    assert findings[0]["detected_text"] == "Miracle Cure"
