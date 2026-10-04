import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from .calculation_workspace import render_calculation_workspace_html
from .clean_renderer import render_clean_pid_html
from .config_matcher import match_configuration
from .config_match_renderer import render_configuration_match_html
from .cleanup import build_cleanup
from .configurations import demo_integrated_configuration_model
from .continuation_renderer import render_continuation_pid_html
from .drafter import build_drafter_instrumented, build_drafter_skeleton
from .dashboard_renderer import render_dashboard_html
from .db_schema import engine_from_url
from .graph_renderer import render_graph_html
from .inspection_graph import build_inspection_graph
from .instrumented_renderer import render_instrumented_pid_html
from .entity_detail_renderer import render_entity_detail_html
from .exporters import (
    export_dexpi_oriented_xml,
    export_dxf_demo,
    export_summary_csv,
    export_visio_vdx_demo,
    simple_text_pdf,
    workspace_pdf_lines,
)
from .hazop_renderer import render_hazop_html
from .skeleton_renderer import render_drafter_skeleton_html
from .summaries import build_bdep_summaries
from .summaries_renderer import render_summaries_html
from .persistence import (
    database_summary,
    ensure_demo_seeded,
    load_approved_configurations,
    load_configuration_match_facts,
    load_object_dossier,
)
from .thread_service import DESIGN_CASES, build_object_dossier
from .topology_compiler import compile_engineering_topology
from .topology_compile_renderer import render_compilation_trace_html
from .simulation import publish_demo_simulation
from .object_detail_renderer import render_object_detail_html
from .publishing import (
    PublishStage,
    PublicationBlocked,
    publication_status,
    publish_all,
    publish_stage,
)

app = FastAPI(title="Digital BDEP Prototype", version="0.9.0")


def _compile_case(design_case_id: str = "CASE-NORMAL"):
    publication = publish_demo_simulation(design_case_id)
    engine = _app_engine()
    with Session(engine) as session:
        facts = load_configuration_match_facts(session)
        definitions = load_approved_configurations(session)
    match = match_configuration(
        publication,
        design_basis_facts=facts,
        definitions=definitions,
    )
    return compile_engineering_topology(publication, match)


@app.get("/api/plant")
def plant_model():
    return _compile_case().plant_model.model_dump(mode="json")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/engineering")


def _app_engine():
    url = os.getenv("DATABASE_URL", "sqlite+pysqlite:///digital_bdep_demo.db")
    engine = engine_from_url(url)
    ensure_demo_seeded(engine)
    return engine


@app.get("/engineering", response_class=HTMLResponse)
def engineering_view():
    compilation = _compile_case("CASE-NORMAL")
    model = compilation.plant_model
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)
    engine = _app_engine()
    with Session(engine) as session:
        dossiers = {
            obj.id: load_object_dossier(session, obj.id)
            for obj in model.objects
        }
        stages = publication_status(session)
    return render_clean_pid_html(
        model,
        plan,
        cleanup,
        dossiers,
        publication_stages=stages,
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_view():
    engine = _app_engine()
    object_ids = [
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
    with Session(engine) as session:
        dossiers = {
            object_id: load_object_dossier(session, object_id)
            for object_id in object_ids
        }
        stages = publication_status(session)
    return render_dashboard_html(dossiers, stages)


@app.get("/engineering-05b", response_class=HTMLResponse)
def engineering_05b():
    model = demo_integrated_configuration_model()
    return render_instrumented_pid_html(model, build_drafter_instrumented(model))


@app.get("/engineering-skeleton", response_class=HTMLResponse)
def engineering_skeleton():
    model = demo_integrated_configuration_model()
    return render_drafter_skeleton_html(model, build_drafter_skeleton(model))


@app.get("/api/design-cases")
def design_cases():
    return [case.model_dump(mode="json") for case in DESIGN_CASES]


@app.get("/api/simulation/{design_case_id}")
def simulation_publication(design_case_id: str):
    return publish_demo_simulation(design_case_id).model_dump(mode="json")


@app.get("/api/pfd-graph/{design_case_id}")
def pfd_graph(design_case_id: str):
    publication = publish_demo_simulation(design_case_id)
    return {
        "simulation_case_id": publication.simulation_case_id,
        "design_case_id": publication.design_case_id,
        "nodes": [item.model_dump(mode="json") for item in publication.equipment],
        "edges": publication.pfd_edges(),
    }


@app.get("/api/configuration-match/{design_case_id}")
def configuration_match(design_case_id: str):
    publication = publish_demo_simulation(design_case_id)
    engine = _app_engine()
    with Session(engine) as session:
        facts = load_configuration_match_facts(session)
        definitions = load_approved_configurations(session)
    return match_configuration(
        publication,
        design_basis_facts=facts,
        definitions=definitions,
    ).model_dump(mode="json")


@app.get("/api/compiled-topology/{design_case_id}")
def compiled_topology(design_case_id: str):
    return _compile_case(design_case_id).model_dump(mode="json")


@app.get("/compiler/{design_case_id}", response_class=HTMLResponse)
def compiler_trace_view(design_case_id: str):
    return render_compilation_trace_html(_compile_case(design_case_id))


@app.get("/configuration-match/{design_case_id}", response_class=HTMLResponse)
def configuration_match_view(design_case_id: str):
    publication = publish_demo_simulation(design_case_id)
    engine = _app_engine()
    with Session(engine) as session:
        facts = load_configuration_match_facts(session)
        definitions = load_approved_configurations(session)
    result = match_configuration(
        publication,
        design_basis_facts=facts,
        definitions=definitions,
    )
    return render_configuration_match_html(publication, result)


@app.get("/api/object/{object_id}/dossier")
def object_dossier(object_id: str):
    model = demo_integrated_configuration_model()
    return build_object_dossier(model, object_id).model_dump(mode="json")


@app.get("/api/db/object/{object_id}/dossier")
def database_object_dossier(object_id: str):
    engine = _app_engine()
    with Session(engine) as session:
        return load_object_dossier(session, object_id).model_dump(mode="json")


@app.get("/object/{object_id}/detail", response_class=HTMLResponse)
def object_detail_view(object_id: str):
    engine = _app_engine()
    with Session(engine) as session:
        dossier = load_object_dossier(session, object_id)
    return render_object_detail_html(dossier)


@app.get("/entity/{entity_id}/detail", response_class=HTMLResponse)
def entity_detail_view(entity_id: str):
    compilation = _compile_case("CASE-NORMAL")
    model = compilation.plant_model
    plan = build_drafter_instrumented(model)
    engine = _app_engine()
    with Session(engine) as session:
        dossiers = {
            obj.id: load_object_dossier(session, obj.id)
            for obj in model.objects
        }

    if entity_id in dossiers:
        return render_object_detail_html(dossiers[entity_id])

    inspection = build_inspection_graph(model, dossiers, plan.routes)
    entity = inspection["entities"].get(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Unknown engineering entity: {entity_id}")
    return render_entity_detail_html(entity)


@app.get("/api/db/summary")
def db_summary():
    engine = _app_engine()
    with Session(engine) as session:
        return database_summary(session)


@app.get("/api/publication-status")
def get_publication_status():
    engine = _app_engine()
    with Session(engine) as session:
        return [
            item.model_dump(mode="json")
            for item in publication_status(session)
        ]


@app.post("/api/publish/{stage}")
def publish_one_stage(stage: PublishStage):
    engine = _app_engine()
    try:
        with Session(engine) as session:
            result = publish_stage(session, stage)
            return result.model_dump(mode="json")
    except PublicationBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/publish-all")
def publish_everything():
    engine = _app_engine()
    try:
        with Session(engine) as session:
            return [
                result.model_dump(mode="json")
                for result in publish_all(session)
            ]
    except PublicationBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/graph", response_class=HTMLResponse)
def graph_view():
    return render_graph_html(_compile_case("CASE-NORMAL").plant_model)


def _full_engineering_context():
    compilation = _compile_case("CASE-NORMAL")
    model = compilation.plant_model
    plan = build_drafter_instrumented(model)
    engine = _app_engine()
    with Session(engine) as session:
        dossiers = {
            obj.id: load_object_dossier(session, obj.id)
            for obj in model.objects
        }
    inspection = build_inspection_graph(model, dossiers, plan.routes)
    return model, plan, dossiers, inspection


@app.get("/workspace/{entity_id}", response_class=HTMLResponse)
def calculation_workspace(entity_id: str):
    model, plan, dossiers, inspection = _full_engineering_context()
    entity = inspection["entities"].get(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Unknown engineering entity: {entity_id}")
    dossier = dossiers.get(entity_id)
    return render_calculation_workspace_html(entity=entity, dossier=dossier)


@app.get("/hazop", response_class=HTMLResponse)
def hazop_view():
    return render_hazop_html()


@app.get("/summaries", response_class=HTMLResponse)
def summaries_view():
    model, plan, dossiers, inspection = _full_engineering_context()
    summaries = build_bdep_summaries(model=model, dossiers=dossiers, inspection=inspection)
    return render_summaries_html(summaries)


@app.get("/engineering-2", response_class=HTMLResponse)
def engineering_continuation_view():
    return render_continuation_pid_html()


@app.get("/export/workspace/{entity_id}.pdf")
def export_workspace_pdf(entity_id: str):
    model, plan, dossiers, inspection = _full_engineering_context()
    entity = inspection["entities"].get(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Unknown engineering entity: {entity_id}")
    dossier = dossiers.get(entity_id)
    payload = simple_text_pdf(
        f"Digital BDEP - {entity.get('tag') or entity_id} Engineering Calculation",
        workspace_pdf_lines(entity, dossier),
    )
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{entity_id}.pdf"'},
    )


@app.get("/export/dexpi.xml")
def export_dexpi_xml():
    model, plan, dossiers, inspection = _full_engineering_context()
    payload = export_dexpi_oriented_xml(model, inspection)
    return Response(
        content=payload,
        media_type="application/xml",
        headers={"Content-Disposition": 'attachment; filename="digital_bdep_dexpi_oriented.xml"'},
    )


@app.get("/export/visio.vdx")
def export_visio_vdx():
    model, plan, dossiers, inspection = _full_engineering_context()
    payload = export_visio_vdx_demo(model, plan)
    return Response(
        content=payload,
        media_type="application/vnd.visio",
        headers={"Content-Disposition": 'attachment; filename="PID-DEMO-001.vdx"'},
    )


@app.get("/export/drawing.dxf")
def export_drawing_dxf():
    model, plan, dossiers, inspection = _full_engineering_context()
    payload = export_dxf_demo(model, plan)
    return Response(
        content=payload,
        media_type="application/dxf",
        headers={"Content-Disposition": 'attachment; filename="PID-DEMO-001.dxf"'},
    )


@app.get("/export/summary/{summary_key}.csv")
def export_one_summary_csv(summary_key: str):
    model, plan, dossiers, inspection = _full_engineering_context()
    summaries = build_bdep_summaries(model=model, dossiers=dossiers, inspection=inspection)
    try:
        payload = export_summary_csv(summaries, summary_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown summary: {summary_key}") from exc
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{summary_key}.csv"'},
    )
