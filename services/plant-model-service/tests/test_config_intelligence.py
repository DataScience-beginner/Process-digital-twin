"""Contract checks for the first agent-assemblable node."""
import pytest
from pydantic import ValidationError

from app.config_intelligence import NodeAssembly, build_pump_node


def test_one_node_has_both_directed_interfaces():
    node = build_pump_node(project_id="PRJ-001", module_id="M-01", pump_tag="P-101")
    assert node.primary_equipment_id in {obj.id for obj in node.graph.objects}
    assert {i.name for i in node.interfaces} == {"upstream", "downstream"}
    assert len(node.graph.connections) == 2
    assert len(node.graph.associations) == 2
    assert node.simulation_binding_status == "unbound"
    assert all(i.stream_id is None and i.line_id is None for i in node.interfaces)


def test_two_project_instances_do_not_share_immutable_object_ids():
    a = build_pump_node(project_id="PRJ-A", module_id="M-01", pump_tag="P-101")
    b = build_pump_node(project_id="PRJ-B", module_id="M-01", pump_tag="P-101")
    assert {o.id for o in a.graph.objects}.isdisjoint({o.id for o in b.graph.objects})


def test_tampered_endpoint_fails_closed():
    node = build_pump_node(project_id="PRJ-001", module_id="M-01", pump_tag="P-101")
    payload = node.model_dump()
    payload["interfaces"][0]["internal_port"] = "NOT_A_PORT"
    with pytest.raises((ValueError, ValidationError, KeyError)):
        NodeAssembly.model_validate(payload)


def test_missing_upstream_connection_fails_closed():
    node = build_pump_node(project_id="PRJ-001", module_id="M-01", pump_tag="P-101")
    payload = node.model_dump()
    payload["graph"]["connections"] = payload["graph"]["connections"][1:]
    with pytest.raises((ValueError, ValidationError)):
        NodeAssembly.model_validate(payload)


def test_missing_required_names_rejected():
    with pytest.raises(ValueError):
        build_pump_node(project_id="PRJ-001", module_id="", pump_tag="P-101")
