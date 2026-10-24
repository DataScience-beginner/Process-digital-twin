"""Implementation-neutral E1 fixture contract; execute with python -m unittest discover -s tests -p 'test_forward_pid_fixture.py'."""
import copy
import json
import unittest
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs" / "forward-pid" / "fixtures"


def read_fixture(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def validate_contract(source, graph):
    errors = []
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    ids = [node["id"] for node in nodes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_node_id")
    node_index = {node["id"]: node for node in nodes}
    port_index = {
        (node["id"], port["name"]): port
        for node in nodes for port in node["ports"]
    }
    if len(port_index) != sum(len(node["ports"]) for node in nodes):
        errors.append("duplicate_port")
    edge_ids = [edge["id"] for edge in edges]
    if len(edge_ids) != len(set(edge_ids)):
        errors.append("duplicate_edge_id")
    adjacency = {}
    for edge in edges:
        start = (edge["from"]["object_id"], edge["from"]["port"])
        finish = (edge["to"]["object_id"], edge["to"]["port"])
        if start not in port_index or finish not in port_index:
            errors.append("missing_port")
            continue
        p_from, p_to = port_index[start], port_index[finish]
        if p_from["direction"] not in ("out", "bidirectional"):
            errors.append("bad_source_direction")
        if p_to["direction"] not in ("in", "bidirectional"):
            errors.append("bad_target_direction")
        if edge["kind"] == "internal_transition":
            if start[0] != finish[0]:
                errors.append("cross_object_internal_transition")
        elif edge["kind"] == "physical_connection" and start[0] == finish[0]:
            errors.append("same_object_physical_connection")
        if edge.get("source_stream_id") not in graph["source_stream_ids"]:
            errors.append("unknown_source_stream")
        adjacency.setdefault(start, []).append(finish)
    start = ("inlet-boundary-1", "OUT")
    end = ("outlet-boundary-1", "IN")
    visited = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for nxt in adjacency.get(current, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    if end not in visited:
        errors.append("disconnected_upstream_downstream")
    if source["event"]["type"] != "pfd.approved" or source["event"]["approval_status"] != "approved":
        errors.append("missing_approved_trigger")
    if source["event"].get("human_prompt") is not None or graph.get("required_human_prompts") != 0:
        errors.append("human_prompt_required")
    config = source["approved_configuration"]
    if config["status"] != "approved" or config["id"] != graph["configuration"]["id"]:
        errors.append("configuration_not_approved")
    if graph.get("drawing_geometry") is not None:
        errors.append("drawing_geometry_in_semantic_graph")
    for prop in source["missing_engineering_data"]:
        if prop not in graph.get("unknown_fields", []) or graph["engineering_values"].get(prop, "absent") is not None:
            errors.append("invented_data")
    if any(node["origin"]["source_revision"] != source["event"]["revision"] for node in nodes):
        errors.append("source_revision_mismatch")
    if not {"str-101", "str-102"}.issubset(set(graph["source_stream_ids"])):
        errors.append("stream_lineage_incomplete")
    if not {"eq-vessel-1", "eq-pump-1"}.issubset(node_index):
        errors.append("pfd_equipment_missing")
    return errors


class ForwardPidFixtureTests(unittest.TestCase):
    def setUp(self):
        self.source = read_fixture("pfd_input.json")
        self.graph = read_fixture("expected_graph.json")

    def test_ground_truth_is_connected_and_unprompted(self):
        self.assertEqual(validate_contract(self.source, self.graph), [])
        self.assertEqual(len(self.graph["nodes"]), 11)
        self.assertEqual(len(self.graph["edges"]), 19)

    def test_pipe_disconnect_fails(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"] = [edge for edge in graph["edges"] if not (
            edge["from"]["object_id"] == "pipe-suc-2"
            and edge["to"]["object_id"] == "nz-p-s"
        )]
        self.assertIn("disconnected_upstream_downstream", validate_contract(self.source, graph))

    def test_nonexistent_port_fails(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"][0]["to"]["port"] = "DOES_NOT_EXIST"
        self.assertIn("missing_port", validate_contract(self.source, graph))

    def test_invalid_source_direction_fails(self):
        graph = copy.deepcopy(self.graph)
        graph["edges"][0]["from"]["port"] = "IN"
        self.assertIn("missing_port", validate_contract(self.source, graph))
        # A physically valid port with the wrong direction must also fail.
        graph = copy.deepcopy(self.graph)
        graph["nodes"][0]["ports"][0]["direction"] = "in"
        self.assertIn("bad_source_direction", validate_contract(self.source, graph))

    def test_tag_rename_does_not_change_ids_or_edges(self):
        graph = copy.deepcopy(self.graph)
        graph["nodes"] = [
            {**node, "tag": "P-900"} if node["id"] == "eq-pump-1" else node
            for node in graph["nodes"]
        ]
        self.assertEqual(validate_contract(self.source, graph), [])
        self.assertEqual(graph["edges"], self.graph["edges"])

    def test_duplicate_identity_fails(self):
        graph = copy.deepcopy(self.graph)
        graph["nodes"][1]["id"] = graph["nodes"][0]["id"]
        self.assertIn("duplicate_node_id", validate_contract(self.source, graph))

    def test_unapproved_configuration_requires_decision(self):
        source = copy.deepcopy(self.source)
        source["approved_configuration"]["status"] = "draft"
        self.assertIn("configuration_not_approved", validate_contract(source, self.graph))

    def test_fabricated_pressure_fails(self):
        graph = copy.deepcopy(self.graph)
        graph["engineering_values"]["pressure"] = 5.5
        self.assertIn("invented_data", validate_contract(self.source, graph))

    def test_unapproved_source_revision_fails(self):
        graph = copy.deepcopy(self.graph)
        graph["nodes"][0]["origin"]["source_revision"] = "B"
        self.assertIn("source_revision_mismatch", validate_contract(self.source, graph))

    def test_synthetic_input_does_not_require_prompt(self):
        source = copy.deepcopy(self.source)
        source["event"]["human_prompt"] = "Please assemble valve"
        self.assertIn("human_prompt_required", validate_contract(source, self.graph))


if __name__ == "__main__":
    unittest.main()
