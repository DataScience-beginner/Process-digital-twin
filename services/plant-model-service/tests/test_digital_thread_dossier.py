from sqlalchemy import inspect

from app.configurations import demo_integrated_configuration_model
from app.db_schema import create_schema
from app.thread_models import RecordDomain
from app.thread_service import build_object_dossier


def _ids(dossier):
    return {criterion.id for criterion in dossier.design_basis}


def test_vessel_dossier_gets_vessel_and_feed_basis_only():
    model = demo_integrated_configuration_model()
    dossier = build_object_dossier(model, "EQ-V101")
    ids = _ids(dossier)
    assert "DBC-FEED-CAPACITY" in ids
    assert "DBC-BL-FEED-PRESSURE" in ids
    assert "DBC-VESSEL-SIZING-MARGIN" in ids
    assert "DBC-PUMP-FLOW-MARGIN" not in ids
    assert "DBC-CV-NORMAL-OPENING" not in ids


def test_pump_dossier_gets_pump_basis_not_vessel_basis():
    model = demo_integrated_configuration_model()
    dossier = build_object_dossier(model, "EQ-P101")
    ids = _ids(dossier)
    assert "DBC-PUMP-FLOW-MARGIN" in ids
    assert "DBC-PUMP-NPSH-MARGIN" in ids
    assert "DBC-VESSEL-HOLDUP" not in ids
    assert "DBC-CV-NORMAL-OPENING" not in ids


def test_fcv_dossier_gets_control_valve_basis_only():
    model = demo_integrated_configuration_model()
    dossier = build_object_dossier(model, "VLV-FCV101")
    ids = _ids(dossier)
    assert "DBC-CV-NORMAL-OPENING" in ids
    assert "DBC-CV-MAX-OPENING" in ids
    assert "DBC-CV-FAIL-FCV101" in ids
    assert "DBC-PUMP-FLOW-MARGIN" not in ids
    assert "DBC-VESSEL-HOLDUP" not in ids


def test_every_displayed_record_has_provenance():
    model = demo_integrated_configuration_model()
    for object_id in ["EQ-V101", "EQ-P101", "VLV-FCV101"]:
        dossier = build_object_dossier(model, object_id)
        assert dossier.design_basis
        for criterion in dossier.design_basis:
            assert criterion.provenance.source_id
        for records in dossier.records.values():
            for record in records:
                assert record.provenance.source_id


def test_dossier_groups_records_by_domain():
    model = demo_integrated_configuration_model()
    pump = build_object_dossier(model, "EQ-P101")
    assert pump.records_for(RecordDomain.SIMULATION)
    assert pump.records_for(RecordDomain.PROCESS_CALC)
    assert pump.records_for(RecordDomain.INSTRUMENTATION)
    assert pump.records_for(RecordDomain.ELECTRICAL)
    assert pump.records_for(RecordDomain.EPC_VENDOR)
    assert pump.records_for(RecordDomain.OPERATIONS)


def test_sql_schema_contains_digital_thread_tables():
    engine = create_schema("sqlite+pysqlite:///:memory:")
    tables = set(inspect(engine).get_table_names())
    expected = {
        "projects",
        "design_basis_revisions",
        "design_basis_criteria",
        "criterion_object_links",
        "design_cases",
        "simulation_cases",
        "equipment",
        "streams",
        "stream_components",
        "engineering_records",
        "record_object_links",
    }
    assert expected <= tables
