from sqlalchemy.orm import Session

from app.clean_renderer import render_clean_pid_html
from app.cleanup import build_cleanup
from app.configurations import demo_integrated_configuration_model
from app.db_schema import create_schema
from app.drafter import build_drafter_instrumented
from app.persistence import load_object_dossier, seed_demo_database
from app.publishing import publish_all


def _render_db_view():
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)
    with Session(engine) as session:
        dossiers = {
            object_id: load_object_dossier(session, object_id)
            for object_id in ["EQ-V101", "EQ-P101", "VLV-FCV101"]
        }
    return render_clean_pid_html(model, plan, cleanup, dossiers)


def test_engineering_view_has_clickable_digital_thread_objects():
    html = _render_db_view()
    assert 'data-object-id="EQ-V101"' in html
    assert 'data-object-id="EQ-P101"' in html
    assert 'data-object-id="VLV-FCV101"' in html
    assert "selectObject('EQ-V101')" in html


def test_sidebar_has_requested_discipline_tabs():
    html = _render_db_view()
    for label in [
        "Overview",
        "Design Basis",
        "Process",
        "P&ID",
        "Calculations",
        "Instrumentation",
        "Mechanical",
        "Electrical",
        "Cost",
        "EPC / Vendor",
        "Operations",
        "History",
    ]:
        assert label in html


def test_persisted_dossiers_are_embedded_with_object_specific_basis():
    html = _render_db_view()
    assert "Vessel sizing flow margin" in html
    assert "Pump rated flow margin" in html
    assert "Target control-valve opening at normal case" in html
    assert "CALC-P101-001" in html
    assert "PUMP_MIN_FLOW_STANDARD_V1" in html


def test_sidebar_exposes_provenance_labels():
    html = _render_db_view()
    assert "Source:" in html
    assert "source_id" in html



def test_connected_pid_routes_remain_present_in_object_view():
    html = _render_db_view()
    for role in [
        "psv_relief",
        "vessel_vent",
        "vessel_drain",
        "pressure_to_pt",
        "pressure_to_pi",
        "level_to_lt",
        "level_to_li",
        "pump_suction_pi",
        "pump_discharge_pi",
        "level_signal",
        "level_control_signal",
        "flow_signal",
        "flow_control_signal",
    ]:
        assert f'data-route-role="{role}"' in html


def test_sidebar_supports_tab_and_properties_modes():
    html = _render_db_view()
    assert "Tabs" in html
    assert "Properties" in html
    assert "property-group-title" in html
    assert 'setInspectorMode(\'properties\')' in html
    for category in [
        "Identification",
        "Design Basis",
        "Process / Simulation",
        "Calculations",
        "P&ID",
        "Instrumentation",
        "Mechanical",
        "Electrical",
        "Cost",
        "EPC / Vendor",
        "Operations",
    ]:
        assert category in html



def test_published_structured_calculation_outputs_are_embedded_and_renderable():
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)

    with Session(engine) as session:
        publish_all(session)

    with Session(engine) as session:
        dossiers = {
            object_id: load_object_dossier(session, object_id)
            for object_id in ["EQ-V101", "EQ-P101", "VLV-FCV101"]
        }

    html = render_clean_pid_html(model, plan, cleanup, dossiers)
    assert "required_holdup_volume_m3" in html
    assert "rated_head_m" in html
    assert "design_cv" in html
    assert 'typeof value==="object"' in html
    assert "structured-value" in html
