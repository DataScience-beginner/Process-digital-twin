from app.clean_renderer import render_clean_pid_html
from app.cleanup import AnnotationKind, build_cleanup
from app.configurations import demo_integrated_configuration_model
from app.drafter import build_drafter_instrumented


def test_cleanup_layer_is_green_for_reference_pid():
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)
    assert cleanup.status == "GREEN"
    assert cleanup.issues == []


def test_cleanup_contains_typed_line_and_offpage_annotations():
    model = demo_integrated_configuration_model()
    cleanup = build_cleanup(build_drafter_instrumented(model))
    kinds = {ann.kind for ann in cleanup.annotations}
    assert AnnotationKind.LINE_TAG in kinds
    assert AnnotationKind.OFFPAGE in kinds
    assert AnnotationKind.NOTE in kinds


def test_clean_view_contains_title_block_and_quality_report():
    model = demo_integrated_configuration_model()
    plan = build_drafter_instrumented(model)
    cleanup = build_cleanup(plan)
    html = render_clean_pid_html(model, plan, cleanup)
    assert "DIGITAL BDEP - P&amp;ID" in html
    assert "Drawing quality" in html
    assert "TO RELIEF HEADER" in html
    assert "L-P101-DIS" in html
    assert "VIEW: ENGINEERING" in html


def test_annotations_do_not_intrude_into_title_block():
    model = demo_integrated_configuration_model()
    cleanup = build_cleanup(build_drafter_instrumented(model))
    assert not any(issue.code == "PROTECTED_ZONE_INTRUSION" for issue in cleanup.issues)
