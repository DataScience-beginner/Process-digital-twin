"""Experiment: preserve named physical ports using *supported* PIDL fields.

This uses upstream PIDLDocument/LineEndpoint/Nozzle and its PidlParser.
Pydantic 'extra=allow' on Line is an explicit PIDL v1.2 extension point.
It does not monkeypatch openpidl, infer data from the E1 expected graph, or
claim upstream PidlParser itself is port-lossless.
"""
from __future__ import annotations

from openpid.dsl.schema import Equipment, InlineItem, Line, LineEndpoint, Nozzle, PIDLDocument
from openpid.parsers.pidl_parser import PidlParser


def encode_port_aware(fixture: dict) -> PIDLDocument:
    lookup = {node["id"]: node for node in fixture["nodes"]}
    equipment = []
    for eid, nozzle_ids in (
        ("eq-vessel-1", ("nz-v-1",)),
        ("eq-pump-1", ("nz-p-s", "nz-p-d")),
    ):
        obj = lookup[eid]
        equipment.append(Equipment(
            id=obj["id"], tag=obj["tag"], symbol_type=obj["type"],
            properties={
                "ports": obj["ports"],
                "origin": obj["origin"],
                "nozzle_details": {
                    nid: {"ports": lookup[nid]["ports"], "origin": lookup[nid]["origin"]}
                    for nid in nozzle_ids
                },
            },
            nozzles=[Nozzle(id=nid, label=lookup[nid]["tag"]) for nid in nozzle_ids],
        ))
    inline = [
        InlineItem(
            id=obj["id"], tag=obj["tag"], symbol_type=obj["type"],
            properties={"ports": obj["ports"], "origin": obj["origin"]},
        )
        for obj in fixture["nodes"]
        if obj["type"] not in ("vertical_separator", "centrifugal_pump", "process_nozzle")
    ]
    lines = [
        Line(
            id=edge["id"],
            **{
                "from": LineEndpoint(
                    ref=edge["from"]["object_id"], port=edge["from"]["port"]
                ),
                "to": LineEndpoint(
                    ref=edge["to"]["object_id"], port=edge["to"]["port"]
                ),
                # Native Line allows extra fields; these two are explicit,
                # namespaced engineering-graph extension fields.
                "x_graph_edge_kind": edge["kind"],
                "x_source_stream_id": edge["source_stream_id"],
            },
        )
        for edge in fixture["edges"]
    ]
    return PIDLDocument(equipment=equipment, inline_items=inline, lines=lines)


def decode_port_aware(doc: PIDLDocument):
    """Use native parser and recover defined fields from the *document itself*.

    Raises on missing/invalid data; never silently fabricates a port.
    """
    graph = PidlParser().parse(doc)
    object_ports = {}
    for eq in doc.equipment:
        if eq.id not in graph.nodes:
            raise ValueError(f"Equipment disappeared: {eq.id}")
        graph.nodes[eq.id].attrs["ports"] = eq.properties.get("ports")
        graph.nodes[eq.id].attrs["origin"] = eq.properties.get("origin")
        object_ports[eq.id] = eq.properties.get("ports")
        details = eq.properties.get("nozzle_details", {})
        for nozzle in eq.nozzles:
            if nozzle.id not in graph.nodes or nozzle.id not in details:
                raise ValueError(f"Nozzle metadata missing: {nozzle.id}")
            graph.nodes[nozzle.id].attrs["ports"] = details[nozzle.id].get("ports")
            graph.nodes[nozzle.id].attrs["origin"] = details[nozzle.id].get("origin")
            object_ports[nozzle.id] = details[nozzle.id].get("ports")
    for item in [*doc.inline_items, *doc.valves]:
        if item.id not in graph.nodes:
            raise ValueError(f"Inline item disappeared: {item.id}")
        graph.nodes[item.id].attrs["ports"] = item.properties.get("ports")
        graph.nodes[item.id].attrs["origin"] = item.properties.get("origin")
        object_ports[item.id] = item.properties.get("ports")

    known_ports = {}
    for oid, ports in object_ports.items():
        if not isinstance(ports, list) or not ports:
            raise ValueError(f"Ports missing for {oid}")
        port_names = [p["name"] for p in ports]
        if len(port_names) != len(set(port_names)):
            raise ValueError(f"Duplicate port for {oid}")
        for port in ports:
            if port["direction"] not in {"in", "out", "bidirectional"}:
                raise ValueError(f"Invalid port direction for {oid}")
            known_ports[(oid, port["name"])] = port

    edge_lookup = {edge.id: edge for edge in graph.edges}
    for line in doc.lines:
        if line.id not in edge_lookup or line.from_node is None or line.to_node is None:
            raise ValueError(f"Lost line endpoints: {line.id}")
        if not line.from_node.port or not line.to_node.port:
            raise ValueError(f"Missing port reference on line {line.id}")
        start = (line.from_node.ref, line.from_node.port)
        end = (line.to_node.ref, line.to_node.port)
        if start not in known_ports or end not in known_ports:
            raise ValueError(f"Unknown port reference on line {line.id}")
        kind = getattr(line, "x_graph_edge_kind", None)
        stream_id = getattr(line, "x_source_stream_id", None)
        if kind not in {"physical_connection", "internal_transition"} or not stream_id:
            raise ValueError(f"Missing required engineering lineage on line {line.id}")
        start_direction = known_ports[start]["direction"]
        end_direction = known_ports[end]["direction"]
        if kind == "physical_connection":
            if start[0] == end[0] or start_direction not in {"out", "bidirectional"} or end_direction not in {"in", "bidirectional"}:
                raise ValueError(f"Physical connection port direction invalid: {line.id}")
        else:
            if start[0] != end[0] or start_direction not in {"in", "bidirectional"} or end_direction not in {"out", "bidirectional"}:
                raise ValueError(f"Internal transition port direction invalid: {line.id}")
        edge = edge_lookup[line.id]
        edge.attrs.update({
            "from_port": line.from_node.port,
            "to_port": line.to_node.port,
            "physical_or_internal": kind,
            "source_stream_id": stream_id,
        })
    return graph
