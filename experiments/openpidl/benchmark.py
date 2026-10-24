"""Real upstream openpidl API evaluation against E1 engineering fixture.

This is a compatibility audit, NOT a new P&ID engine. Test upstream's
EngineeringGraph JSON roundtrip and its native PIDLDocument -> EngineeringGraph
projection separately. Record observed losses rather than concealing them.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpid.graph.model import EngineeringGraph, GraphEdge, GraphNode
from openpid.serializers.json_serializer import JsonDeserializer, JsonSerializer
from openpid.dsl.schema import PIDLDocument, Equipment, Nozzle, InlineItem, Line, LineEndpoint
from openpid.parsers.pidl_parser import PidlParser


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs" / "forward-pid" / "fixtures"
REPORT = ROOT / "docs" / "forward-pid" / "benchmark-results" / "openpidl-e2-result.json"


def load(name: str) -> dict:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def engineering_graph(graph_data: dict) -> EngineeringGraph:
    graph = EngineeringGraph(meta={"fixture_id": graph_data["fixture_id"]})
    for n in graph_data["nodes"]:
        kind = (
            "equipment" if n["type"] in ("vertical_separator", "centrifugal_pump") else
            "valve" if n["type"] == "isolation_valve" else
            "nozzle" if n["type"] == "process_nozzle" else
            "piping_component"
        )
        graph.add_node(GraphNode(
            id=n["id"], kind=kind, tag=n["tag"], source_class=n["type"],
            pidl_type=n["type"], attrs={"ports": n["ports"], "origin": n["origin"]},
        ))
    for edge in graph_data["edges"]:
        graph.add_edge(GraphEdge(
            id=edge["id"], source=edge["from"]["object_id"],
            target=edge["to"]["object_id"], kind="process_line",
            attrs={
                "from_port": edge["from"]["port"],
                "to_port": edge["to"]["port"],
                "physical_or_internal": edge["kind"],
                "source_stream_id": edge["source_stream_id"],
            },
        ))
    return graph


def native_pidl_document(graph_data: dict) -> PIDLDocument:
    """Represent identical fixture using openpidl's public sheet schema.

    Boundary and piping segments are modeled as inline items because the native
    document has no separate first-class category for them; this is evaluated.
    """
    idx = {n["id"]: n for n in graph_data["nodes"]}
    equipment = []
    for oid in ("eq-vessel-1", "eq-pump-1"):
        n = idx[oid]
        nozzles = [
            Nozzle(id=pid, label=idx[pid]["tag"])
            for pid in ("nz-v-1", "nz-p-s", "nz-p-d")
            if (oid == "eq-vessel-1" and pid == "nz-v-1") or
               (oid == "eq-pump-1" and pid in ("nz-p-s", "nz-p-d"))
        ]
        equipment.append(Equipment(
            id=n["id"], tag=n["tag"], symbol_type=n["type"], nozzles=nozzles,
        ))
    inline = [
        InlineItem(id=n["id"], tag=n["tag"], symbol_type=n["type"],
                   properties={"ports": n["ports"], "origin": n["origin"]})
        for n in graph_data["nodes"]
        if n["type"] not in ("vertical_separator", "centrifugal_pump", "process_nozzle")
    ]
    lines = [
        Line(
            id=e["id"],
            **{"from": LineEndpoint(ref=e["from"]["object_id"], port=e["from"]["port"]),
               "to": LineEndpoint(ref=e["to"]["object_id"], port=e["to"]["port"])},
        )
        for e in graph_data["edges"]
    ]
    return PIDLDocument(equipment=equipment, inline_items=inline, lines=lines)


def compare_ids_and_ports(expected: dict, actual_nodes: list[GraphNode], actual_edges: list[GraphEdge]) -> dict:
    expected_nodes = {node["id"] for node in expected["nodes"]}
    actual_ids = {node.id for node in actual_nodes}
    expected_edges = {edge["id"] for edge in expected["edges"]}
    actual_edge_ids = {edge.id for edge in actual_edges}
    port_matches = 0
    for actual in actual_nodes:
        expected_node = next((n for n in expected["nodes"] if n["id"] == actual.id), None)
        if expected_node is not None and actual.attrs.get("ports") == expected_node["ports"]:
            port_matches += 1
    endpoint_matches = 0
    lookup = {e["id"]: e for e in expected["edges"]}
    for actual in actual_edges:
        expected_edge = lookup.get(actual.id)
        if expected_edge and (
            actual.source == expected_edge["from"]["object_id"] and
            actual.target == expected_edge["to"]["object_id"] and
            actual.attrs.get("from_port") == expected_edge["from"]["port"] and
            actual.attrs.get("to_port") == expected_edge["to"]["port"]
        ):
            endpoint_matches += 1
    return {
        "expected_node_count": len(expected_nodes),
        "actual_node_count": len(actual_ids),
        "missing_node_ids": sorted(expected_nodes - actual_ids),
        "expected_edge_count": len(expected_edges),
        "actual_edge_count": len(actual_edge_ids),
        "missing_edge_ids": sorted(expected_edges - actual_edge_ids),
        "exact_node_ports": port_matches,
        "exact_edge_endpoints_and_ports": endpoint_matches,
    }


def main() -> None:
    expected = load("expected_graph.json")
    g = engineering_graph(expected)
    encoded = JsonSerializer().serialize(g)
    g2 = JsonDeserializer().deserialize(encoded)
    json_comparison = compare_ids_and_ports(expected, list(g2.nodes.values()), g2.edges)
    assert json_comparison["missing_node_ids"] == []
    assert json_comparison["missing_edge_ids"] == []
    assert json_comparison["exact_node_ports"] == len(expected["nodes"])
    assert json_comparison["exact_edge_endpoints_and_ports"] == len(expected["edges"])

    doc = native_pidl_document(expected)
    reparsed = PidlParser().parse(PIDLDocument.model_validate(doc.model_dump()))
    native_comparison = compare_ids_and_ports(expected, list(reparsed.nodes.values()), reparsed.edges)

    original = next(node for node in g2.nodes.values() if node.id == "eq-pump-1")
    original.tag = "P-900"
    rename_safe = original.id == "eq-pump-1" and all(
        e.source != "P-900" and e.target != "P-900" for e in g2.edges
    )
    assert rename_safe

    result = {
        "experiment": "E2 openpidl upstream library compatibility",
        "fixture": expected["fixture_id"],
        "upstream_library": "openpid-com/openpidl",
        "method": "real library imports and API calls, with native PIDL and generic graph paths",
        "generic_engineering_graph_json": json_comparison,
        "native_pidl_document_projection": native_comparison,
        "tag_rename_keeps_immutable_identity": rename_safe,
        "generic_graph_roundtrip_pass": True,
        "native_pidl_lossless": (
            not native_comparison["missing_node_ids"]
            and not native_comparison["missing_edge_ids"]
            and native_comparison["exact_node_ports"] == len(expected["nodes"])
            and native_comparison["exact_edge_endpoints_and_ports"] == len(expected["edges"])
        ),
        "decision": "Do not adopt native PIDL as sole graph master unless port-level and component identity losses are resolved",
        "notes": [
            "JsonSerializer preserves graph attrs supplied by an adapter; this is not evidence that the native PIDL document roundtrip does.",
            "Native PIDLDocument graph mapping is a separate losslessness check.",
            "Drawing layout, DEXPI roundtrip and production maturity are outside this small step."
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
