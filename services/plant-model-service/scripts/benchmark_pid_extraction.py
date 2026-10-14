"""Benchmark P&ID tag and proposed graph recovery against isolated fixture truth.

No model is trained on or given expected_graph.json during extraction.
This tool reports raw candidate precision/recall, not approved-plant accuracy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.pid_pipeline import build_pid_extraction
from scripts.generate_pid_corpus import generate


def score_sets(found: set, expected: set) -> dict:
    tp = len(found & expected)
    fp = len(found - expected)
    fn = len(expected - found)
    precision = tp / (tp + fp) if tp + fp else (1.0 if not expected else 0.0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round((2 * precision * recall / (precision + recall))
                    if precision + recall else 0.0, 4),
        "missed": sorted(expected - found, key=str),
        "unexpected": sorted(found - expected, key=str),
    }


def _pairs(items):
    return {
        tuple(sorted(edge))
        for edge in items
    }


def evaluate_fixture(file_path: Path, tags: list, connections: list) -> dict:
    _, extracted = build_pid_extraction(
        file_path.read_bytes(), file_path.name, ocr=False
    )
    actual_tags = {t["tag"] for t in extracted["candidates"]}
    actual_pairs = _pairs([
        (e["tag_a"], e["tag_b"])
        for e in extracted["connection_proposals"]
        if e["type"] == "process_candidate"
    ])
    expected_pairs = _pairs(connections)
    symbol_matches = {
        item["tag"] for item in extracted["symbol_hypotheses"]
        if item["geometry_id"]
    }
    return {
        "fixture": file_path.name,
        "tag_candidates": score_sets(actual_tags, set(tags)),
        "symbol_geometry_recall": score_sets(symbol_matches, set(tags)),
        "process_route_hypotheses": score_sets(actual_pairs, expected_pairs),
        "source_evidence_complete": all(
            e["source_segment_ids"] and e["source_route_points"]
            for e in extracted["connection_proposals"]
        ),
        "process_routes": [
            {
                "tags": [e["tag_a"], e["tag_b"]],
                "stroke_count": e["hops"],
                "page": e["page"],
                "review_status": e["review_status"],
            }
            for e in extracted["connection_proposals"]
            if e["type"] == "process_candidate"
        ],
        "warnings": extracted["warnings"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus", type=Path, default=Path("data/pid_corpus/generated")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("data/pid_corpus/benchmark_report.json")
    )
    args = parser.parse_args()
    if not (args.corpus / "expected_graph.json").is_file():
        generate(args.corpus)
    truth = json.loads((args.corpus / "expected_graph.json").read_text())
    examples = [
        (truth["fixture"], truth["expected_tags"],
         truth["known_process_adjacencies"]),
        (truth["extra_fixture"], ["V-101", "P-101", "FCV-101"],
         truth["expected_elbow_adjacencies"]),
    ]
    result = {
        "description": "Synthetic fixture only; not real P&ID industrial accuracy",
        "fixtures": [evaluate_fixture(args.corpus / name, tags, pairs)
                     for name, tags, pairs in examples],
        "review_required": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
