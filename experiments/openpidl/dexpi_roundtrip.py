"""E2.3: actual upstream openpidl PIDL -> Proteus XML -> PIDL test.

The experiment records losses; expected incompatibilities do not masquerade
as a passing data-fidelity assessment. Synthetic benchmark only.
"""
from __future__ import annotations

import json
import sys
import tempfile
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

from openpid.compilers.pidl_compiler import PidlCompiler
from openpid.io.proteus.reader import ProteusReader
from openpid.io.proteus.writer import ProteusWriter
from openpid.parsers.pidl_parser import PidlParser

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from benchmark import compare_ids_and_ports, load
from port_adapter import decode_port_aware, encode_port_aware

ROOT = HERE.parents[1]
REPORT = ROOT / "docs" / "forward-pid" / "benchmark-results" / "dexpi-roundtrip-e23.json"


def main() -> None:
    fixture = load("expected_graph.json")
    expected_objects = {n["id"] for n in fixture["nodes"]}
    expected_edges = {e["id"] for e in fixture["edges"]}
    report = {
        "experiment": "E2.3 actual openpidl native PIDL -> DEXPI Proteus XML -> PIDL",
        "fixture": fixture["fixture_id"],
        "expected_nodes": len(expected_objects),
        "expected_edges": len(expected_edges),
        "status": "not_run",
        "native_dexpi_roundtrip_lossless": False,
        "stages": {},
        "warnings": [],
    }

    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "benchmark.xml"
        try:
            doc = encode_port_aware(fixture)
            # Ensure PIDL JSON transport works before DEXPI.
            doc = type(doc).model_validate_json(doc.model_dump_json(by_alias=True))
            graph = decode_port_aware(doc)
            report["stages"]["input_pidl"] = {
                "equipment": len(doc.equipment),
                "inline_items": len(doc.inline_items),
                "nozzles": sum(len(e.nozzles) for e in doc.equipment),
                "lines": len(doc.lines),
                "input_graph": compare_ids_and_ports(fixture, list(graph.nodes.values()), graph.edges),
            }

            ProteusWriter().write(graph, xml_path)
            root = ET.parse(xml_path).getroot()
            count_tags = ("Equipment", "Nozzle", "PipingNetworkSegment", "PipingComponent", "Connection")
            report["stages"]["dexpi_xml"] = {
                "root_tag": root.tag,
                "element_counts": {tag: len(root.findall(".//" + tag)) for tag in count_tags},
                "bytes": xml_path.stat().st_size,
            }
            reader_graph = ProteusReader().read(xml_path)
            rd_nodes = list(reader_graph.nodes.values())
            rd_edges = list(reader_graph.edges)
            report["stages"]["read_graph"] = {
                "comparison": compare_ids_and_ports(fixture, rd_nodes, rd_edges),
                "kinds": {kind: len(reader_graph.nodes_by_kind(kind)) for kind in ["equipment", "valve", "nozzle", "piping_component", "instrument"]},
                "sample_nodes": [{"id":n.id,"kind":n.kind,"dexpi_id":n.attrs.get("dexpi_id")} for n in rd_nodes[:10]],
                "sample_edges": [{"id":e.id,"source":e.source,"target":e.target,"attrs_keys":sorted(e.attrs.keys())[:12]} for e in rd_edges[:5]],
            }
            compiled = PidlCompiler().compile(reader_graph)
            compiled = type(compiled).model_validate_json(compiled.model_dump_json(by_alias=True))
            parsed = PidlParser().parse(compiled)
            final = compare_ids_and_ports(fixture, list(parsed.nodes.values()), parsed.edges)
            report["stages"]["compiled_pidl"] = {
                "equipment": len(compiled.equipment),
                "inline_items": len(compiled.inline_items),
                "valves": len(compiled.valves),
                "lines": len(compiled.lines),
                "nozzles": sum(len(e.nozzles) for e in compiled.equipment),
                "comparison": final,
            }
            report["native_dexpi_roundtrip_lossless"] = (
                not final["missing_node_ids"] and not final["missing_edge_ids"]
                and final["exact_node_ports"] == len(expected_objects)
                and final["exact_edge_endpoints_and_ports"] == len(expected_edges)
            )
            report["status"] = "completed"
            if not report["native_dexpi_roundtrip_lossless"]:
                report["warnings"].append("Native DEXPI exchange is not lossless for this fixture; preserve a detailed project graph outside the interchange until improved.")
            if report["stages"]["dexpi_xml"]["element_counts"]["PipingNetworkSegment"] > 0:
                report["warnings"].append("Inspect whether internal equipment transitions were emitted as piping network segments.")
        except Exception as exc:
            report["status"] = "conversion_failed"
            report["error_type"] = type(exc).__name__
            report["error_message"] = str(exc)
            report["traceback_tail"] = traceback.format_exc().splitlines()[-12:]
            report["warnings"].append("The unmodified upstream conversion route failed; this is an interoperability gap, not an engineering validation success.")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print("E2_3_RESULT_BEGIN")
    print(json.dumps(report, indent=2, default=str))
    print("E2_3_RESULT_END")
    # A completed incompatible result is a valid audit finding.
    # A failed invocation is captured explicitly; CI must not falsely claim losslessness.
    assert report["status"] in {"completed", "conversion_failed"}


if __name__ == "__main__":
    main()
