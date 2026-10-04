from app.configurations import demo_integrated_configuration_model
from app.models import Nozzle
from app.views import build_demo_pid_view


def test_equipment_connectivity_is_through_explicit_nozzle_nodes():
    model = demo_integrated_configuration_model()
    protected_equipment = {"EQ-V101", "EQ-P101"}
    for connection in model.connections:
        if connection.kind.value != "process":
            continue
        assert connection.source.object_id not in protected_equipment
        assert connection.target.object_id not in protected_equipment


def test_nozzles_are_first_class_nodes_with_equipment_parent():
    model = demo_integrated_configuration_model()
    nozzles = [obj for obj in model.objects if isinstance(obj, Nozzle)]
    assert len(nozzles) >= 12
    assert {n.parent_equipment_id for n in nozzles} == {"EQ-V101", "EQ-P101"}


def test_digital_thread_traversal_reaches_pump_from_vessel():
    model = demo_integrated_configuration_model()
    affected = set(model.impact_walk("EQ-V101"))
    assert "NOZ-V101-LIQ" in affected
    assert "VLV-LCV101" in affected
    assert "NOZ-P101-SUC" in affected
    assert "EQ-P101" in affected


def test_drawing_view_links_shapes_and_routes_to_semantic_graph():
    model = demo_integrated_configuration_model()
    view = build_demo_pid_view(model)
    view.validate_against(model)

    object_ids = {obj.id for obj in model.objects}
    edge_ids = {c.id for c in model.connections} | {a.id for a in model.associations}

    assert {r.semantic_object_id for r in view.representations} <= object_ids
    assert {r.semantic_edge_id for r in view.routes} <= edge_ids
    assert any(r.semantic_object_id == "NOZ-V101-LIQ" for r in view.representations)
    assert any(r.semantic_edge_id == "C-LIQ-01" for r in view.routes)
