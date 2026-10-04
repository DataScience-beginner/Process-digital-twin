from sqlalchemy.orm import Session

from app.clean_renderer import render_clean_pid_html
from app.cleanup import build_cleanup
from app.configurations import demo_integrated_configuration_model
from app.db_schema import create_schema
from app.drafter import build_drafter_instrumented
from app.inspection_graph import build_inspection_graph
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
    assert "selectEntity('EQ-V101')" in html


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



def test_all_visible_pid_entities_are_selectable_not_only_major_equipment():
    html = _render_db_view()
    for object_id in [
        "EQ-V101",
        "VLV-PSV101",
        "VLV-VENT101",
        "VLV-DRAIN101",
        "INS-PT101",
        "INS-PI101",
        "INS-LT101",
        "INS-LI101",
        "INS-LIC101",
        "VLV-LCV101",
        "VLV-XV101",
        "EQ-P101",
        "INS-PI101S",
        "INS-PI101D",
        "JUNC-P101-DIS",
        "VLV-NRV101",
        "VLV-XV102",
        "BOUND-PRODUCT",
        "INS-FT101",
        "INS-FIC101",
        "VLV-FCV101",
    ]:
        assert f'data-object-id="{object_id}"' in html
        assert f"selectEntity('{object_id}')" in html


def test_process_lines_and_signal_routes_are_selectable_entities():
    html = _render_db_view()
    for entity_id in [
        "LINE-1102",
        "LINE-1103",
        "LINE-1190",
        "LINE-PSV101",
        "LINE-VENT101",
        "LINE-DRAIN101",
        "SIGNAL-LT101-LIC101",
        "SIGNAL-LIC101-LCV101",
        "SIGNAL-FT101-FIC101",
        "SIGNAL-FIC101-FCV101",
    ]:
        assert f'data-route-entity-id="{entity_id}"' in html


def test_relationship_inspector_reverses_context_for_equipment_and_line():
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)
    with Session(engine) as session:
        publish_all(session)
    with Session(engine) as session:
        dossiers = {
            obj.id: load_object_dossier(session, obj.id)
            for obj in model.objects
        }

    graph = build_inspection_graph(model, dossiers, plan.routes)
    entities = graph["entities"]

    vessel_lines = {item["id"] for item in entities["EQ-V101"]["connected_lines"]}
    assert "LINE-1102" in vessel_lines
    assert "LINE-1190" in vessel_lines
    assert "LINE-PSV101" in vessel_lines
    assert "LINE-1103" not in vessel_lines

    suction_path = [item["id"] for item in entities["LINE-1102"]["path"]]
    assert suction_path == [
        "EQ-V101",
        "NOZ-V101-LIQ",
        "VLV-LCV101",
        "VLV-XV101",
        "NOZ-P101-SUC",
        "EQ-P101",
    ]

    assert entities["LINE-1102"]["from"]["id"] == "EQ-V101"
    assert entities["LINE-1102"]["to"]["id"] == "EQ-P101"
    assert entities["VLV-PSV101"]["parent_equipment"]["id"] == "EQ-V101"
    assert entities["VLV-FCV101"]["parent_equipment"]["id"] == "EQ-P101"
    assert entities["VLV-XV101"]["parent_equipment"]["id"] == "EQ-P101"


def test_lines_are_contextual_not_dumped_into_every_object_calculation_tab():
    html = _render_db_view()
    assert "Connected Lines / Connections" in html
    assert "Connected Nodes" in html
    assert "Connected line calculations are opened by selecting the line itself." in html



def test_engineering_workspace_keeps_existing_features_in_three_pane_shell():
    html = _render_db_view()
    for text in [
        "Workspace",
        "P&ID 001 — Engineering",
        "Plant Model / Digital Thread",
        "P&ID 002 — Continuation",
        "Project Dashboard",
        "HAZOP",
        "BDEP Summaries",
        "Configuration Match",
        "Compiler / Plant Data",
        "Publish Project Stages",
        "Discipline Inspector",
        "Sketch / Stencil Palette",
        "Drafting Assistance",
        "Exports",
        "Tabs",
        "Properties",
        "Detailed View",
        "Pop out / Calculation Workspace",
    ]:
        assert text in html

    assert 'id="leftSidebar"' in html
    assert 'id="pidCanvas"' in html
    assert 'id="rightSidebar"' in html
    assert "toggleLeftSidebar()" in html
    assert "toggleRightSidebar()" in html


def test_workspace_supports_drag_drop_stencils_guided_connectors_and_autocorrect_options():
    html = _render_db_view()
    for stencil in [
        "vessel",
        "pump",
        "exchanger",
        "manual_valve",
        "control_valve",
        "psv",
        "instrument",
        "boundary",
    ]:
        assert f'data-stencil="{stencil}"' in html

    for text in [
        "Guided Connector",
        "Auto-correct",
        "Validate Draft",
        "Prepare Change Set",
        "Grid snap",
        "Orthogonal route",
        "Avoid overlap",
        "Keep in sheet",
        "Auto-guided",
        "Process line",
        "Control signal",
        "Impulse / sensing",
        "PROPOSED_NOT_APPLIED",
    ]:
        assert text in html

    for function_name in [
        "canvasDrop",
        "createDraftObject",
        "createDraftConnection",
        "autoCorrectDrafts",
        "validateDrafts",
        "prepareChangeSet",
    ]:
        assert f"function {function_name}" in html



def test_left_sidebar_is_category_model_browser_not_cluttered_menu():
    html = _render_db_view()
    for label in [
        "Engineering Model Browser",
        "Equipment",
        "Instruments",
        "Streams",
        "Piping / Lines",
        "Valves",
        "Control Loops / Signals",
        "Instrument Connections",
        "Boundaries / Off-page",
        "Drawings / Views",
    ]:
        assert label in html

    assert 'id="modelBrowser"' in html
    assert 'id="modelSearch"' in html
    assert "function renderModelBrowser" in html
    assert "function selectFromBrowser" in html


def test_browser_child_selection_focuses_canvas_and_populates_properties():
    html = _render_db_view()
    assert "function focusCanvasEntity" in html
    assert "focusCanvasEntity(id)" in html
    assert 'setInspectorMode("properties")' in html
    assert "Focused: " in html
    assert "Fit Drawing" in html
    assert 'svg.setAttribute("viewBox","0 0 1120 690")' in html


def test_drawing_selection_has_no_blue_round_or_blue_route_highlight():
    html = _render_db_view()
    assert "rgba(37,99,235,.16)" not in html
    assert "stroke:#1d4ed8" not in html
    assert "route-hit:hover{{stroke:rgba(15,23,42,.08)}}" in html


def test_drawing_quality_is_a_right_inspector_tab_not_bottom_information_panel():
    html = _render_db_view()
    assert '["quality","Drawing / QA"]' in html
    assert 'id="drawingQualityTemplate"' in html
    assert '<div class="section">Drawing quality</div>' not in html
