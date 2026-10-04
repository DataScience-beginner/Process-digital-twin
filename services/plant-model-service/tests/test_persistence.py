from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.db_schema import create_schema
from app.persistence import (
    database_summary,
    load_object_dossier,
    seed_demo_database,
)


def test_seeded_database_has_canonical_topology_and_case_results():
    engine = create_schema("sqlite+pysqlite:///:memory:")
    counts = seed_demo_database(engine)

    assert counts["equipment"] == 2
    assert counts["streams"] == 4
    assert counts["simulation_cases"] == 3
    assert counts["stream_case_results"] == 12
    assert counts["stream_components"] == 24


def test_db_backed_pump_dossier_is_object_specific():
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)

    with Session(engine) as session:
        dossier = load_object_dossier(session, "EQ-P101")

    ids = {criterion.id for criterion in dossier.design_basis}
    assert "DBC-PUMP-FLOW-MARGIN" in ids
    assert "DBC-PUMP-NPSH-MARGIN" in ids
    assert "DBC-VESSEL-HOLDUP" not in ids
    assert "DBC-CV-NORMAL-OPENING" not in ids


def test_db_backed_fcv_dossier_preserves_provenance():
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)

    with Session(engine) as session:
        dossier = load_object_dossier(session, "VLV-FCV101")

    assert dossier.design_basis
    assert all(item.provenance.source_id for item in dossier.design_basis)
    records = [record for group in dossier.records.values() for record in group]
    assert records
    assert all(record.provenance.source_id for record in records)


def test_database_summary_reflects_seeded_thread():
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)

    with Session(engine) as session:
        summary = database_summary(session)

    assert summary["projects"] == 1
    assert summary["design_cases"] == 3
    assert summary["simulation_cases"] == 3
    assert summary["equipment"] == 2
    assert summary["streams"] == 4
    assert summary["stream_case_results"] == 12


def test_alembic_upgrade_creates_core_schema(tmp_path):
    db_path = tmp_path / "alembic_test.db"
    service_root = Path(__file__).resolve().parents[1]
    config = Config(str(service_root / "alembic.ini"))
    config.set_main_option("script_location", str(service_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db_path}")

    command.upgrade(config, "head")

    from sqlalchemy import create_engine, inspect

    tables = set(inspect(create_engine(f"sqlite+pysqlite:///{db_path}")).get_table_names())
    assert {
        "projects",
        "design_basis_revisions",
        "design_basis_criteria",
        "criterion_object_links",
        "design_cases",
        "simulation_cases",
        "equipment",
        "streams",
        "stream_case_results",
        "stream_components",
        "engineering_records",
        "record_object_links",
    } <= tables
