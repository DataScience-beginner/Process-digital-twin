from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from .clean_renderer import render_clean_pid_html
from .cleanup import build_cleanup
from .configurations import demo_integrated_configuration_model
from .drafter import build_drafter_instrumented, build_drafter_skeleton
from .graph_renderer import render_graph_html
from .instrumented_renderer import render_instrumented_pid_html
from .skeleton_renderer import render_drafter_skeleton_html
from .thread_service import DESIGN_CASES, build_object_dossier

app = FastAPI(title="Digital BDEP Prototype", version="0.5.3")


@app.get("/api/plant")
def plant_model():
    return demo_integrated_configuration_model().model_dump(mode="json")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/engineering")


@app.get("/engineering", response_class=HTMLResponse)
def engineering_view():
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)
    return render_clean_pid_html(model, plan, cleanup)


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


@app.get("/api/object/{object_id}/dossier")
def object_dossier(object_id: str):
    model = demo_integrated_configuration_model()
    return build_object_dossier(model, object_id).model_dump(mode="json")


@app.get("/graph", response_class=HTMLResponse)
def graph_view():
    return render_graph_html(demo_integrated_configuration_model())
