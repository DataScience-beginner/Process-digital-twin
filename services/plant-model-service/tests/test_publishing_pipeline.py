import pytest
from sqlalchemy.orm import Session

from app.db_schema import create_schema
from app.persistence import load_object_dossier, seed_demo_database
from app.publishing import (
    PublicationBlocked,
    PublishStage,
    publication_status,
    publish_all,
    publish_stage,
)


def _engine():
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)
    return engine


def test_stage_dependency_blocks_out_of_order_publication():
    engine = _engine()
    with Session(engine) as session:
        with pytest.raises(PublicationBlocked, match="requires published stages"):
            publish_stage(session, PublishStage.PROCESS)


def test_publish_all_completes_all_current_stages_in_order():
    engine = _engine()
    with Session(engine) as session:
        results = publish_all(session)
        assert [item.stage for item in results] == [
            PublishStage.DESIGN_BASIS,
            PublishStage.SIMULATION,
            PublishStage.CONFIGURATION,
            PublishStage.PROCESS,
            PublishStage.INSTRUMENTATION,
            PublishStage.MECHANICAL,
            PublishStage.COSTING,
        ]

    with Session(engine) as session:
        statuses = publication_status(session)
        assert all(item.status == "published" for item in statuses)


def test_process_publisher_writes_vessel_pump_and_psv_basis():
    engine = _engine()
    with Session(engine) as session:
        for stage in [
            PublishStage.DESIGN_BASIS,
            PublishStage.SIMULATION,
            PublishStage.CONFIGURATION,
            PublishStage.PROCESS,
        ]:
            publish_stage(session, stage)

    with Session(engine) as session:
        vessel = load_object_dossier(session, "EQ-V101")
        pump = load_object_dossier(session, "EQ-P101")

    vessel_ids = {
        item.id
        for records in vessel.records.values()
        for item in records
    }
    pump_ids = {
        item.id
        for records in pump.records.values()
        for item in records
    }
    assert "CALC-V101-HOLDUP" in vessel_ids
    assert "RELIEF-PSV101-BASIS" in vessel_ids
    assert "CALC-P101-RATED-FLOW" in pump_ids


def test_instrumentation_publisher_writes_cv_and_dcs_records():
    engine = _engine()
    with Session(engine) as session:
        for stage in [
            PublishStage.DESIGN_BASIS,
            PublishStage.SIMULATION,
            PublishStage.CONFIGURATION,
            PublishStage.PROCESS,
            PublishStage.INSTRUMENTATION,
        ]:
            publish_stage(session, stage)

    with Session(engine) as session:
        fcv = load_object_dossier(session, "VLV-FCV101")
        pump = load_object_dossier(session, "EQ-P101")

    fcv_ids = {
        item.id
        for records in fcv.records.values()
        for item in records
    }
    pump_ids = {
        item.id
        for records in pump.records.values()
        for item in records
    }
    assert "CALC-FCV101-CV" in fcv_ids
    assert "DCS-FIC101-LOOP" in fcv_ids
    assert "INST-FT101-RANGE" in pump_ids

    cv = next(
        item
        for records in fcv.records.values()
        for item in records
        if item.id == "CALC-FCV101-CV"
    )
    assert cv.value["design_cv"] > cv.value["raw_cv"] > 0


def test_mechanical_and_costing_publishers_replace_placeholders():
    engine = _engine()
    with Session(engine) as session:
        publish_all(session)

    with Session(engine) as session:
        vessel = load_object_dossier(session, "EQ-V101")
        pump = load_object_dossier(session, "EQ-P101")
        fcv = load_object_dossier(session, "VLV-FCV101")

    all_vessel = [item for records in vessel.records.values() for item in records]
    all_pump = [item for records in pump.records.values() for item in records]
    all_fcv = [item for records in fcv.records.values() for item in records]

    mech_vessel = next(item for item in all_vessel if item.id == "MECH-V101")
    mech_pump = next(item for item in all_pump if item.id == "MECH-P101")
    cost_vessel = next(item for item in all_vessel if item.id == "COST-V101")
    cost_pump = next(item for item in all_pump if item.id == "COST-P101")
    cost_fcv = next(item for item in all_fcv if item.id == "COST-FCV101")

    assert mech_vessel.status == "mechanical_basis_published_demo"
    assert mech_pump.value["preliminary_motor_kw"] > 0
    assert cost_vessel.value > 0
    assert cost_pump.value > 0
    assert cost_fcv.value > 0


def test_psv_publisher_does_not_fake_final_orifice_sizing():
    engine = _engine()
    with Session(engine) as session:
        for stage in [
            PublishStage.DESIGN_BASIS,
            PublishStage.SIMULATION,
            PublishStage.CONFIGURATION,
            PublishStage.PROCESS,
        ]:
            publish_stage(session, stage)

    with Session(engine) as session:
        vessel = load_object_dossier(session, "EQ-V101")

    psv = next(
        item
        for records in vessel.records.values()
        for item in records
        if item.id == "RELIEF-PSV101-BASIS"
    )
    assert psv.value["final_orifice_area"].startswith("TBD")
    assert psv.metadata["qualified_service_required"] is True
