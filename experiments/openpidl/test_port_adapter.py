"""Execute against the actual upstream installed openpidl dependency."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark import compare_ids_and_ports, load
from port_adapter import decode_port_aware, encode_port_aware
from openpid.dsl.schema import PIDLDocument


class PortAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load("expected_graph.json")

    def document_roundtrip(self, fixture=None):
        doc = encode_port_aware(fixture or self.fixture)
        # The intermediate transport is *real* PIDL document JSON, not an
        # in-memory instance passed straight back without serialization.
        return PIDLDocument.model_validate_json(doc.model_dump_json(by_alias=True))

    def test_lossless_ports_and_ids(self):
        graph = decode_port_aware(self.document_roundtrip())
        result = compare_ids_and_ports(
            self.fixture, list(graph.nodes.values()), graph.edges
        )
        self.assertEqual(result["missing_node_ids"], [])
        self.assertEqual(result["missing_edge_ids"], [])
        self.assertEqual(result["exact_node_ports"], 11)
        self.assertEqual(result["exact_edge_endpoints_and_ports"], 19)
        self.assertTrue(all(
            edge.attrs["source_stream_id"] in ("str-101", "str-102")
            for edge in graph.edges
        ))

    def test_missing_named_endpoint_port_fails_closed(self):
        doc = self.document_roundtrip()
        doc.lines[0].from_node.port = None
        with self.assertRaises(ValueError):
            decode_port_aware(doc)

    def test_unknown_port_fails_closed(self):
        doc = self.document_roundtrip()
        doc.lines[0].to_node.port = "UNKNOWN_PORT"
        with self.assertRaises(ValueError):
            decode_port_aware(doc)

    def test_invalid_flow_direction_fails_closed(self):
        doc = self.document_roundtrip()
        doc.equipment[0].properties["ports"][0]["direction"] = "out"
        with self.assertRaises(ValueError):
            decode_port_aware(doc)

    def test_removed_lineage_fails_closed(self):
        doc = self.document_roundtrip()
        doc.lines[0].__pydantic_extra__.pop("x_source_stream_id")
        with self.assertRaises(ValueError):
            decode_port_aware(doc)

    def test_tag_rename_keeps_ids_and_connections(self):
        doc = self.document_roundtrip()
        for eq in doc.equipment:
            if eq.id == "eq-pump-1":
                eq.tag = "P-900"
        graph = decode_port_aware(doc)
        self.assertIn("eq-pump-1", graph.nodes)
        self.assertEqual(graph.nodes["eq-pump-1"].tag, "P-900")
        self.assertEqual({e.id for e in graph.edges}, {x["id"] for x in self.fixture["edges"]})


if __name__ == "__main__":
    unittest.main()
