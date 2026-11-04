from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main


def make_db():
    engine = create_engine("sqlite:///:memory:")
    main.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def test_velora_numeric_matching_and_duplicate_grouping():
    db = make_db()
    try:
        workspace = main.Workspace(name="VELORA", description="Regression fixture")
        db.add(workspace)
        db.flush()
        db.add_all([
            main.ApprovedFact(
                workspace_id=workspace.id,
                subject="VELORA Vitamin C Serum",
                attribute="Vitamin C concentration",
                approved_value="10",
                unit="%",
                verified=True,
            ),
            main.Terminology(
                workspace_id=workspace.id,
                term="100% safe",
                replacement="Dermatologically tested",
                term_type="prohibited",
                case_sensitive=False,
            ),
        ])
        db.commit()

        content = (
            "VELORA Vitamin C Serum\n\n"
            "Our formula contains 20% Vitamin C.\n"
            "Eliminates dark spots in 3 days.\n"
            "100% safe for everyone."
        )
        findings = main.evaluate(db, workspace.id, content)

        # One numeric contradiction only: 20% Vitamin C.
        numeric = [f for f in findings if f["finding_type"] == "fact_contradiction"]
        assert len(numeric) == 1
        assert numeric[0]["detected_text"] == "20%"
        assert numeric[0]["evidence"][0]["source_type"] == "approved_fact"

        # The terminology and absolute-claim detectors are grouped into one finding.
        safe = [f for f in findings if f["detected_text"].lower() == "100% safe"]
        assert len(safe) == 1
        assert safe[0]["finding_type"] == "terminology_violation"
        assert "Absolute claims require explicit substantiation" in safe[0]["explanation"]

        # The two separate claim warnings remain visible and advisory.
        assert any(f["finding_type"] == "strong_outcome_claim" for f in findings)
        assert any(f["finding_type"] == "time_bound_claim" for f in findings)
        assert len(findings) == 4
    finally:
        db.close()
