from sqlalchemy.orm import Session

from app.calculation_workspace import render_calculation_workspace_html
from app.cleanup import build_cleanup
from app.configurations import demo_integrated_configuration_model
from app.continuation import continuation_section
from app.continuation_renderer import render_continuation_pid_html
from app.db_schema import create_schema
from app.drafter import build_drafter_instrumented
from app.dwg_adapter import DwgConverterUnavailable, convert_dxf_to_dwg, dwg_converter_status
from app.exporters import (
    export_dexpi_oriented_xml,
    export_dxf_demo,
    export_summary_csv,
    export_visio_vdx_demo,
    extract_svg_document,
    simple_text_pdf,
    summary_pdf_lines,
    workspace_pdf_lines,
)
from app.hazop import build_demo_hazop, hazop_rows_for_entity
from app.hazop_renderer import render_hazop_html
from app.inspection_graph import build_inspection_graph
from app.persistence import load_object_dossier, seed_demo_database
from app.publishing import publish_all
from app.summaries import build_bdep_summaries
from app.summaries_renderer import render_summaries_html


def _context():
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
    inspection = build_inspection_graph(model, dossiers, plan.routes)
    return model, plan, engine, dossiers, inspection


def _record(dossier, record_id):
    return next(
        record
        for records in dossier.records.values()
        for record in records
        if record.id == record_id
    )


def test_psv_demo_selects_standard_orifice_with_full_trace_and_safety_gate():
    model, plan, engine, dossiers, inspection = _context()
    relief = _record(dossiers["VLV-PSV101"], "RELIEF-PSV101-BASIS")

    assert relief.value["selected_orifice"] == "Q"
    assert 6.38 < relief.value["required_orifice_area_in2"] < 11.05
    assert relief.value["selected_orifice_area_in2"] == 11.05
    assert relief.value["selected_capacity_tph"] > relief.value["relief_load_tph"]
    assert relief.value["final_orifice_area"].startswith("TBD")

    detail = relief.metadata["calculation_detail"]
    trace = detail["trace"]
    assert len(trace["steps"]) == 10
    assert trace["steps"][7]["title"] == "Calculate required effective area"
    assert trace["steps"][8]["result"].startswith("Q /")
    assert any(
        check["result"] == "GATED"
        for check in trace["validation_checks"]
    )
    assert len(detail["relief_scenarios"]) >= 4


def test_vessel_pump_fcv_and_line_calculations_have_step_by_step_trace():
    model, plan, engine, dossiers, inspection = _context()

    vessel = _record(dossiers["EQ-V101"], "CALC-V101-HOLDUP")
    pump = _record(dossiers["EQ-P101"], "CALC-P101-RATED-FLOW")
    fcv = _record(dossiers["VLV-FCV101"], "CALC-FCV101-CV")
    line = _record(dossiers["EQ-P101"], "LINE-1102-SIZING")

    assert len(vessel.metadata["calculation_detail"]["trace"]["steps"]) >= 4
    assert len(pump.metadata["calculation_detail"]["trace"]["steps"]) >= 9
    assert len(fcv.metadata["calculation_detail"]["trace"]["steps"]) >= 6
    assert len(line.metadata["calculation_detail"]["trace"]["steps"]) >= 8
    assert line.metadata["calculation_detail"]["trace"]["selection_checks"]


def test_workspace_looks_like_engineering_calculation_datasheet_with_discipline_tabs():
    model, plan, engine, dossiers, inspection = _context()
    entity = inspection["entities"]["VLV-PSV101"]
    html = render_calculation_workspace_html(
        entity=entity,
        dossier=dossiers["VLV-PSV101"],
    )

    for text in [
        "Engineering Calculation & Datasheet Workspace",
        "Process / Safety",
        "Instrumentation / DCS",
        "Technical / Mechanical",
        "Electrical",
        "Cost Estimate",
        "Vendor / EPC",
        "Operations",
        "HAZOP",
        "Provenance / Audit",
        "Input Sources / Provenance",
        "Calculation Steps",
        "Candidate / Selection Checks",
        "Validation Checks",
        "Relief Scenario Register",
        "Selected demo standard orifice",
        "Q",
        "PDF",
        "DEXPI XML",
        "Visio VDX",
        "CAD DXF",
    ]:
        assert text in html


def test_hazop_demonstrator_links_real_entities_and_calculations():
    data = build_demo_hazop()
    assert len(data["nodes"]) == 3
    assert sum(len(node["rows"]) for node in data["nodes"]) >= 7

    psv_rows = hazop_rows_for_entity("VLV-PSV101")
    assert any(row["row_id"] == "HZ-001" for row in psv_rows)

    suction_rows = hazop_rows_for_entity("LINE-1102")
    assert {row["row_id"] for row in suction_rows} >= {"HZ-002", "HZ-101", "HZ-103"}

    html = render_hazop_html()
    assert "HAZOP Digital-Thread Demonstrator" in html
    assert "Blocked or restricted vapor outlet" in html
    assert "/workspace/VLV-PSV101" in html
    assert "RELIEF-PSV101-BASIS" in html


def test_second_pid_continues_same_line_across_sheet_boundary():
    section = continuation_section()
    assert section["incoming_reference"]["line_entity_id"] == "LINE-1103"
    assert section["incoming_reference"]["from_drawing"] == "PID-DEMO-001"
    assert section["incoming_reference"]["to_drawing"] == "PID-DEMO-002"

    incoming = next(line for line in section["lines"] if line["id"] == "LINE-1103")
    assert incoming["line_number"] == '6"-HC-1103-CS150'
    assert incoming["continued_from"] == "PID-DEMO-001"

    html = render_continuation_pid_html()
    assert "FROM PID-DEMO-001" in html
    assert '6&quot;-HC-1103-CS150' in html
    assert "E-201" in html
    assert "V-201" in html
    assert "LCV-201" in html


def test_generated_summaries_cover_engineering_registers_and_csv_export():
    model, plan, engine, dossiers, inspection = _context()
    summaries = build_bdep_summaries(
        model=model,
        dossiers=dossiers,
        inspection=inspection,
    )

    for key in [
        "equipment_list",
        "stream_list",
        "line_list",
        "valve_list",
        "control_valve_list",
        "instrument_index",
        "control_loop_list",
        "psv_relief_summary",
        "calculation_register",
        "technical_summary",
        "cost_summary",
        "publication_summary",
    ]:
        assert key in summaries

    assert any(row["tag"] == "V-101" for row in summaries["equipment_list"])
    assert any(row["line_number"] == '8"-HC-1102-CS150' for row in summaries["line_list"])
    assert any(row["selected_orifice"] == "Q" for row in summaries["psv_relief_summary"])
    assert any(row["trace_id"] == "TRACE-CALC-P101-RATED-DUTY" for row in summaries["calculation_register"])

    csv_bytes = export_summary_csv(summaries, "line_list")
    assert b"line_number" in csv_bytes
    assert b'8\"-HC-1102-CS150' in csv_bytes or b'8""-HC-1102-CS150' in csv_bytes

    html = render_summaries_html(summaries)
    assert "Generated BDEP Summaries" in html
    assert "Equipment List" in html
    assert "PSV / Relief Summary" in html
    assert "Calculation Register" in html


def test_dexpi_visio_dxf_and_pdf_exports_are_real_files_with_semantic_content():
    model, plan, engine, dossiers, inspection = _context()
    summaries = build_bdep_summaries(
        model=model,
        dossiers=dossiers,
        inspection=inspection,
    )

    dexpi = export_dexpi_oriented_xml(model, inspection)
    assert dexpi.startswith(b"<?xml")
    assert b'DEXPI-2.0.1-oriented-demo' in dexpi
    assert b'schemaValidation="PENDING"' in dexpi
    assert b"EQ-V101" in dexpi
    assert b"LINE-1102" in dexpi

    visio = export_visio_vdx_demo(model, plan)
    assert visio.startswith(b"<?xml")
    assert b"VisioDocument" in visio
    assert b"V-101" in visio

    dxf = export_dxf_demo(model, plan)
    assert b"SECTION" in dxf
    assert b"ENTITIES" in dxf
    assert b"PROCESS" in dxf

    entity = inspection["entities"]["EQ-P101"]
    pdf = simple_text_pdf(
        "Digital BDEP P-101",
        workspace_pdf_lines(entity, dossiers["EQ-P101"]),
    )
    assert pdf.startswith(b"%PDF-1.4")
    assert b"TRACE-CALC-P101-RATED-DUTY" not in pdf  # trace ID is not forced into compact text export
    assert len(pdf) > 1000



def test_mechanical_and_cost_tabs_also_have_step_by_step_trace():
    model, plan, engine, dossiers, inspection = _context()

    mech_vessel = _record(dossiers["EQ-V101"], "MECH-V101")
    mech_pump = _record(dossiers["EQ-P101"], "MECH-P101")
    cost_vessel = _record(dossiers["EQ-V101"], "COST-V101")
    cost_total = _record(dossiers["EQ-P101"], "COST-PACKAGE-TOTAL")

    for record in [mech_vessel, mech_pump, cost_vessel, cost_total]:
        trace = record.metadata["calculation_detail"]["trace"]
        assert trace["steps"]
        assert trace["validation_checks"]
        assert trace["limitations"]
        assert trace["downstream_consumers"]



def test_dwg_export_is_real_adapter_not_fake_binary(monkeypatch):
    monkeypatch.delenv("DWG_CONVERTER_CMD", raising=False)
    status = dwg_converter_status()
    assert status["configured"] is False
    assert status["input_format"] == "DXF"
    assert status["output_format"] == "DWG"

    try:
        convert_dxf_to_dwg(b"0\nEOF\n")
    except DwgConverterUnavailable as exc:
        assert "not configured" in str(exc).lower()
    else:
        raise AssertionError("DWG adapter must not fabricate a DWG when converter is unavailable")



def test_line_sizing_is_full_hydraulic_trace_not_velocity_only():
    model, plan, engine, dossiers, inspection = _context()
    line = _record(dossiers["EQ-P101"], "LINE-1102-SIZING")

    assert line.value["selected_nps_in"] == 8.0
    assert line.value["selected_internal_diameter_in"] > 7.9
    assert line.value["design_reynolds"] > 100000
    assert 0 < line.value["design_friction_factor"] < 0.1
    assert line.value["design_friction_dp_bar"] < line.value["friction_dp_limit_bar"]

    detail = line.metadata["calculation_detail"]
    trace = detail["trace"]
    assert len(trace["steps"]) >= 11
    titles = {step["title"] for step in trace["steps"]}
    assert "Calculate Reynolds number" in titles
    assert "Calculate Darcy friction factor" in titles
    assert "Calculate frictional pressure drop" in titles
    assert any(
        row["pressure_drop_check"] == "PASS"
        for row in trace["selection_checks"]
        if row["candidate_nps_in"] == 8.0
    )
    assert {"reynolds", "friction_factor", "friction_dp_bar"} <= set(detail["case_results"][0])



def test_standalone_svg_and_consolidated_summary_pdf_exports():
    model, plan, engine, dossiers, inspection = _context()
    summaries = build_bdep_summaries(
        model=model,
        dossiers=dossiers,
        inspection=inspection,
    )

    mock_html = '<!doctype html><html><body><svg viewBox="0 0 100 100"><line x1="0" y1="0" x2="100" y2="100"/></svg></body></html>'
    svg = extract_svg_document(mock_html)
    assert svg.startswith(b'<?xml version="1.0"')
    assert b'xmlns="http://www.w3.org/2000/svg"' in svg
    assert b"<line" in svg

    lines = summary_pdf_lines(summaries)
    assert any("EQUIPMENT LIST" in line for line in lines)
    assert any("LINE LIST" in line for line in lines)
    assert any("PSV / RELIEF SUMMARY" in line for line in lines)

    pdf = simple_text_pdf("Digital BDEP Summaries", lines)
    assert pdf.startswith(b"%PDF-1.4")
    assert len(pdf) > 1500
