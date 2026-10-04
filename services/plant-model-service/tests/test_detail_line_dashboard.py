from sqlalchemy.orm import Session

from app.cleanup import build_cleanup
from app.clean_renderer import render_clean_pid_html
from app.configurations import demo_integrated_configuration_model
from app.dashboard_renderer import render_dashboard_html
from app.db_schema import create_schema
from app.drafter import build_drafter_instrumented
from app.object_detail_renderer import render_object_detail_html
from app.entity_detail_renderer import render_entity_detail_html
from app.inspection_graph import build_inspection_graph
from app.persistence import load_object_dossier, seed_demo_database
from app.publishing import publication_status, publish_all
from app.simulation import publish_demo_simulation


OBJECT_IDS = [
    "EQ-V101",
    "EQ-P101",
    "VLV-PSV101",
    "VLV-LCV101",
    "VLV-FCV101",
    "INS-PT101",
    "INS-LT101",
    "INS-LIC101",
    "INS-FT101",
    "INS-FIC101",
]


def _published_engine():
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)
    with Session(engine) as session:
        publish_all(session)
    return engine


def test_simulation_has_four_digit_engineering_stream_numbers():
    publication = publish_demo_simulation("CASE-NORMAL")
    assert [stream.stream_number for stream in publication.streams] == [
        "1100", "1101", "1102", "1103"
    ]
    assert [stream.simulator_stream_id for stream in publication.streams] == [
        "S-100", "S-101", "S-102", "S-103"
    ]


def test_process_publication_sizes_suction_discharge_and_recycle_lines():
    engine = _published_engine()
    with Session(engine) as session:
        pump = load_object_dossier(session, "EQ-P101")

    line_records = {
        record.id: record
        for records in pump.records.values()
        for record in records
        if record.id.startswith("LINE-")
    }
    assert line_records["LINE-1102-SIZING"].value["selected_nps_in"] == 8.0
    assert line_records["LINE-1103-SIZING"].value["selected_nps_in"] == 6.0
    assert line_records["LINE-1190-SIZING"].value["selected_nps_in"] == 4.0
    assert line_records["LINE-1102-SIZING"].value["line_number"] == '8"-HC-1102-CS150'
    assert line_records["LINE-1103-SIZING"].value["line_number"] == '6"-HC-1103-CS150'
    assert line_records["LINE-1190-SIZING"].value["line_number"] == '4"-HC-1190-CS150'


def test_line_sizing_metadata_contains_case_results_and_governing_reason():
    engine = _published_engine()
    with Session(engine) as session:
        pump = load_object_dossier(session, "EQ-P101")

    record = next(
        record
        for records in pump.records.values()
        for record in records
        if record.id == "LINE-1102-SIZING"
    )
    detail = record.metadata["calculation_detail"]
    assert len(detail["case_results"]) == 3
    assert {row["case"] for row in detail["case_results"]} == {
        "Normal", "Maximum", "Turndown"
    }
    assert detail["governing_case"] == "Maximum"
    assert "highest published liquid flow" in detail["governing_reason"]


def test_psv_detail_contains_scenario_register_and_selection_rationale():
    engine = _published_engine()
    with Session(engine) as session:
        psv = load_object_dossier(session, "VLV-PSV101")

    relief = next(
        record
        for records in psv.records.values()
        for record in records
        if record.id == "RELIEF-PSV101-BASIS"
    )
    detail = relief.metadata["calculation_detail"]
    assert len(detail["relief_scenarios"]) >= 4
    assert detail["preliminary_selected_scenario"] == "Blocked vapor outlet"
    assert "not declared the final project governing relief case" in detail["selection_reason"]
    assert relief.metadata["qualified_service_required"] is True


def test_object_detail_page_renders_inputs_criteria_cases_and_psv_scenarios():
    engine = _published_engine()
    with Session(engine) as session:
        pump = load_object_dossier(session, "EQ-P101")
        psv = load_object_dossier(session, "VLV-PSV101")

    pump_html = render_object_detail_html(pump)
    assert "Inputs" in pump_html
    assert "Criteria / Limits" in pump_html
    assert "Case Results" in pump_html
    assert "Governing case" in pump_html
    assert '8&quot;-HC-1102-CS150' in pump_html

    psv_html = render_object_detail_html(psv)
    assert "Relief Scenario Register" in psv_html
    assert "Why Considered" in psv_html
    assert "Preliminary selected scenario" in psv_html


def test_engineering_view_uses_published_line_numbers_and_detail_controls():
    engine = _published_engine()
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)

    with Session(engine) as session:
        dossiers = {
            object_id: load_object_dossier(session, object_id)
            for object_id in OBJECT_IDS
        }
        stages = publication_status(session)

    html = render_clean_pid_html(
        model,
        plan,
        cleanup,
        dossiers,
        publication_stages=stages,
    )
    assert '8&quot;-HC-1102-CS150' in html
    assert '6&quot;-HC-1103-CS150' in html
    assert '4&quot;-HC-1190-CS150' in html
    assert "↗ Detailed View" in html
    assert "⧉ Pop out" in html
    assert "Relief Scenario Register" in html


def test_dashboard_shows_completion_matrix_and_project_cost():
    engine = _published_engine()
    with Session(engine) as session:
        dossiers = {
            object_id: load_object_dossier(session, object_id)
            for object_id in OBJECT_IDS
        }
        stages = publication_status(session)

    html = render_dashboard_html(dossiers, stages)
    assert "Primary Equipment Completion Matrix" in html
    assert "Demo project/section estimate" in html
    assert "V-101" in html
    assert "P-101" in html
    assert "FCV-101" in html
    assert "EPC / Vendor" in html
    assert "/object/EQ-P101/detail" in html



def test_engineering_view_keeps_stage_buttons_tabs_properties_and_detail_as_additive():
    engine = _published_engine()
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)

    with Session(engine) as session:
        dossiers = {
            object_id: load_object_dossier(session, object_id)
            for object_id in OBJECT_IDS
        }
        stages = publication_status(session)

    html = render_clean_pid_html(
        model,
        plan,
        cleanup,
        dossiers,
        publication_stages=stages,
    )

    for label in [
        "Publish Design Basis",
        "Publish Simulation",
        "Select Configuration",
        "Publish Process / Safety",
        "Publish Instrumentation / DCS",
        "Publish Technical / Mechanical",
        "Publish Cost Estimate",
        "Publish All",
        "Tabs",
        "Properties",
        "Technical / Mechanical",
        "Cost Estimate",
        "↗ Detailed View",
        "⧉ Pop out",
    ]:
        assert label in html


def test_technical_and_cost_records_have_full_detail_metadata():
    engine = _published_engine()
    with Session(engine) as session:
        vessel = load_object_dossier(session, "EQ-V101")
        pump = load_object_dossier(session, "EQ-P101")

    all_vessel = [
        record
        for records in vessel.records.values()
        for record in records
    ]
    all_pump = [
        record
        for records in pump.records.values()
        for record in records
    ]

    mech_vessel = next(record for record in all_vessel if record.id == "MECH-V101")
    mech_pump = next(record for record in all_pump if record.id == "MECH-P101")
    cost_vessel = next(record for record in all_vessel if record.id == "COST-V101")
    cost_pump = next(record for record in all_pump if record.id == "COST-P101")

    for record in [mech_vessel, mech_pump, cost_vessel, cost_pump]:
        detail = record.metadata["calculation_detail"]
        assert detail["inputs"]
        assert detail["criteria"]
        assert detail["outputs"]
        assert detail["method"]


def test_dashboard_rolls_child_instruments_and_valves_into_primary_equipment():
    engine = _published_engine()
    with Session(engine) as session:
        dossiers = {
            object_id: load_object_dossier(session, object_id)
            for object_id in OBJECT_IDS
        }
        stages = publication_status(session)

    html = render_dashboard_html(dossiers, stages)
    assert "Primary equipment" in html
    assert "Small valves/instruments are child objects" in html
    assert "PSV-101" in html
    assert "LCV-101" in html
    assert "FCV-101" in html
    # Only the two major equipment detail links should be dashboard rows.
    assert html.count('/object/EQ-V101/detail') == 1
    assert html.count('/object/EQ-P101/detail') == 1
    assert '/object/VLV-FCV101/detail' not in html



def test_line_sizing_has_full_equation_trace_and_candidate_selection():
    engine = _published_engine()
    with Session(engine) as session:
        pump = load_object_dossier(session, "EQ-P101")

    record = next(
        record
        for records in pump.records.values()
        for record in records
        if record.id == "LINE-1102-SIZING"
    )
    trace = record.metadata["calculation_detail"]["trace"]

    assert trace["trace_id"] == "TRACE-LINE-1102-SIZING"
    assert len(trace["steps"]) >= 8
    assert trace["steps"][1]["equation"] == "Q = W × 1000 / (rho × 3600)"
    assert trace["steps"][1]["substitution"]
    assert trace["selection_checks"]

    selected = next(
        row for row in trace["selection_checks"]
        if row["candidate_nps_in"] == 8.0
    )
    smaller = next(
        row for row in trace["selection_checks"]
        if row["candidate_nps_in"] == 6.0
    )
    assert selected["result"] == "PASS"
    assert smaller["result"] == "FAIL"

    checks = {row["check"]: row["result"] for row in trace["validation_checks"]}
    assert checks["Selected velocity <= Design Basis limit"] == "PASS"
    assert checks["Previous smaller standard size rejected when applicable"] == "PASS"
    assert trace["assumptions"]
    assert trace["limitations"]
    assert trace["downstream_consumers"]


def test_pump_vessel_and_fcv_have_full_calculation_traces():
    engine = _published_engine()
    with Session(engine) as session:
        vessel = load_object_dossier(session, "EQ-V101")
        pump = load_object_dossier(session, "EQ-P101")
        fcv = load_object_dossier(session, "VLV-FCV101")

    vessel_record = next(
        record for records in vessel.records.values() for record in records
        if record.id == "CALC-V101-HOLDUP"
    )
    pump_record = next(
        record for records in pump.records.values() for record in records
        if record.id == "CALC-P101-RATED-FLOW"
    )
    fcv_record = next(
        record for records in fcv.records.values() for record in records
        if record.id == "CALC-FCV101-CV"
    )

    vessel_trace = vessel_record.metadata["calculation_detail"]["trace"]
    pump_trace = pump_record.metadata["calculation_detail"]["trace"]
    fcv_trace = fcv_record.metadata["calculation_detail"]["trace"]

    assert len(vessel_trace["steps"]) == 4
    assert any("V_holdup" in step["equation"] for step in vessel_trace["steps"])

    assert len(pump_trace["steps"]) == 9
    assert any("P_hyd" in step["equation"] for step in pump_trace["steps"])
    assert any("P_shaft" in step["equation"] for step in pump_trace["steps"])
    assert any("P_motor" in step["equation"] for step in pump_trace["steps"])

    assert len(fcv_trace["steps"]) == 6
    assert any("Kv" in step["equation"] for step in fcv_trace["steps"])
    opening_checks = {
        row["check"]: row["result"]
        for row in fcv_trace["validation_checks"]
    }
    assert opening_checks["Normal opening target"] == "PENDING TRIM/CHARACTERISTIC"


def test_psv_trace_is_explicitly_gated_not_fake_final_sizing():
    engine = _published_engine()
    with Session(engine) as session:
        psv = load_object_dossier(session, "VLV-PSV101")

    record = next(
        record for records in psv.records.values() for record in records
        if record.id == "RELIEF-PSV101-BASIS"
    )
    trace = record.metadata["calculation_detail"]["trace"]
    checks = {row["check"]: row["result"] for row in trace["validation_checks"]}

    assert trace["qualification"].startswith("Safety-critical")
    assert checks["Final governing scenario established"] == "GATED"
    assert checks["Final orifice sizing permitted"] == "GATED"
    assert any("not a final" in item.lower() for item in trace["limitations"])


def test_detailed_renderers_show_full_calculation_trace():
    engine = _published_engine()
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)

    with Session(engine) as session:
        dossiers = {
            obj.id: load_object_dossier(session, obj.id)
            for obj in model.objects
        }
        pump = dossiers["EQ-P101"]

    pump_html = render_object_detail_html(pump)
    assert "Full Calculation Trace" in pump_html
    assert "Equation / Substitution Steps" in pump_html
    assert "Validation Checks" in pump_html
    assert "Limitations / Qualification Gaps" in pump_html

    inspection = build_inspection_graph(model, dossiers, plan.routes)
    line_html = render_entity_detail_html(inspection["entities"]["LINE-1102"])
    assert "Full Calculation Trace" in line_html
    assert "Candidate / Selection Checks" in line_html
    assert "Q = W × 1000 / (rho × 3600)" in line_html
    assert "6.0" in line_html
    assert "FAIL" in line_html
    assert "8.0" in line_html
    assert "PASS" in line_html


def test_engineering_view_embeds_full_trace_ui():
    engine = _published_engine()
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)

    with Session(engine) as session:
        dossiers = {
            obj.id: load_object_dossier(session, obj.id)
            for obj in model.objects
        }
        stages = publication_status(session)

    html = render_clean_pid_html(
        model, plan, cleanup, dossiers, publication_stages=stages
    )
    assert "Full Calculation Trace" in html
    assert "Equation / Substitution Steps" in html
    assert "Candidate / Selection Checks" in html
    assert "Limitations / Qualification Gaps" in html
    assert "TRACE-LINE-1102-SIZING" in html
