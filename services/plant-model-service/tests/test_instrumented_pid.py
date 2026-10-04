from app.configurations import demo_integrated_configuration_model
from app.drafter import DraftPass, build_drafter_instrumented
from app.instrumented_renderer import render_instrumented_pid_html


def test_instrumented_plan_adds_expected_drafter_passes():
    plan = build_drafter_instrumented(demo_integrated_configuration_model())
    assert DraftPass.PROTECTION in plan.passes_completed
    assert DraftPass.INSTRUMENTATION in plan.passes_completed
    assert DraftPass.SIGNALS in plan.passes_completed
    assert DraftPass.ANNOTATION in plan.passes_completed


def test_instrumented_view_contains_protection_and_control_loops():
    model = demo_integrated_configuration_model()
    html = render_instrumented_pid_html(model, build_drafter_instrumented(model))
    for tag in [
        "PSV-101", "PT-101", "PI-101", "LT-101", "LI-101", "LIC-101",
        "PI-101S", "PI-101D", "FT-101", "FIC-101", "FCV-101", "LCV-101",
    ]:
        assert tag in html


def test_instrumented_routes_remain_orthogonal():
    plan = build_drafter_instrumented(demo_integrated_configuration_model())
    for route in plan.routes:
        for a, b in zip(route.points, route.points[1:]):
            assert a.x == b.x or a.y == b.y


def test_process_skeleton_is_preserved_when_instruments_are_added():
    plan = build_drafter_instrumented(demo_integrated_configuration_model())
    by_role = {route.role: route for route in plan.routes}
    assert by_role["primary_suction"].points[0].x == 220
    assert by_role["primary_suction"].points[0].y == 405
    assert by_role["primary_discharge"].points[0].x == 716
    assert by_role["minimum_flow_recycle"].points[0].x == 785
