from app.configurations import demo_integrated_configuration_model
from app.graph_renderer import render_graph_html
from app.renderer import render_pid_html


def test_engineering_view_hides_graph_nozzle_nodes():
    html = render_pid_html(demo_integrated_configuration_model())
    assert "Digital BDEP — Engineering View" in html
    assert "nozzle-node" not in html
    assert 'href="/graph"' in html


def test_graph_view_exposes_semantic_nodes_and_edges():
    html = render_graph_html(demo_integrated_configuration_model())
    assert "Digital BDEP — Graph View" in html
    assert 'data-semantic-object-id="NOZ-V101-LIQ"' in html
    assert 'data-semantic-edge-id="C-LIQ-01"' in html
    assert 'href="/engineering"' in html
