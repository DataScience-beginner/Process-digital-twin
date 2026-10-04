from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .configurations import demo_integrated_configuration_model
from .renderer import render_pid_html

app = FastAPI(title="Digital BDEP Prototype", version="0.3.1")


@app.get("/api/plant")
def plant_model():
    return demo_integrated_configuration_model().model_dump(mode="json")


@app.get("/", response_class=HTMLResponse)
def viewer():
    return render_pid_html(demo_integrated_configuration_model())
