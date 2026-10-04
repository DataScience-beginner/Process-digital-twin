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


def test_vessel_liquid_nozzle_has_visible_stub_and_route_starts_at_stub_end():
    model = demo_integrated_configuration_model()
    plan = build_drafter_skeleton(model)
    primary = next(route for route in plan.routes if route.role == "primary_suction")
    assert primary.points[0].x == 220
    assert primary.points[0].y == 405

    html = render_drafter_skeleton_html(model, plan)
    assert 'x1="220" y1="393" x2="220" y2="405"' in html


def test_control_valve_stem_runs_through_body_center_to_diaphragm():
    model = demo_integrated_configuration_model()
    plan = build_drafter_skeleton(model)
    html = render_drafter_skeleton_html(model, plan)
    assert 'x1="395" y1="430" x2="395" y2="407"' in html
    assert 'x1="383" y1="407" x2="407" y2="407"' in html
