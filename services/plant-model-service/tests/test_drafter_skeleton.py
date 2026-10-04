from app.configurations import demo_integrated_configuration_model
from app.drafter import DraftPass, build_drafter_skeleton
from app.skeleton_renderer import render_drafter_skeleton_html


def test_drafter_skeleton_passes_are_staged():
    model = demo_integrated_configuration_model()
    plan = build_drafter_skeleton(model)
    assert plan.status == "GREEN"
    assert plan.passes_completed[:4] == [
        DraftPass.SHEET_INTENT,
        DraftPass.EQUIPMENT,
        DraftPass.NOZZLES,
        DraftPass.PRIMARY_PIPING,
    ]


def test_primary_and_recycle_corridors_are_present():
    model = demo_integrated_configuration_model()
    plan = build_drafter_skeleton(model)
    roles = {route.role for route in plan.routes}
    assert {"primary_suction", "primary_discharge", "minimum_flow_recycle"} <= roles


def test_all_skeleton_routes_are_orthogonal():
    model = demo_integrated_configuration_model()
    plan = build_drafter_skeleton(model)
    for route in plan.routes:
        for a, b in zip(route.points, route.points[1:]):
            assert a.x == b.x or a.y == b.y


def test_skeleton_view_defers_instrumentation():
    model = demo_integrated_configuration_model()
    plan = build_drafter_skeleton(model)
    html = render_drafter_skeleton_html(model, plan)
    assert "PT-101" not in html
    assert "LT-101" not in html
    assert "FIC-101" not in html
    assert "P-101" in html
    assert "V-101" in html
    assert "LCV-101" in html
