from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from .configurations import demo_integrated_configuration_model
from .graph_renderer import render_graph_html
from .renderer import render_pid_html

app = FastAPI(title="Digital BDEP Prototype", version="0.5.0")


@app.get("/api/plant")
def plant_model():
    return demo_integrated_configuration_model().model_dump(mode="json")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/engineering")


@app.get("/engineering", response_class=HTMLResponse)
def engineering_view():
    return render_pid_html(demo_integrated_configuration_model())


@app.get("/graph", response_class=HTMLResponse)
def graph_view():
    return render_graph_html(demo_integrated_configuration_model())
