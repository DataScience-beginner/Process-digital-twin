"""Independent, repeatable 10-sheet *real* P&ID pilot, with annotation handoff.

This command extracts evidence from 10 consecutive source P&IDs (Pāhala
drawings P-101 and P-201...P-209) but deliberately creates EMPTY gold labels.
Engineers must independently label symbols, tags and connected edges before
any precision/recall can be reported. The source PDF is local and is never
included in the output report.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import fitz

from app.pid_client_intake import extract_single_page, preflight_pdf
from app.pid_pipeline import build_pid_extraction

# Pāhala engineering drawing INDEX (official document's first page),
# not inferred from the extraction engine itself.
SHEETS = [
    (9, "P-101"), (10, "P-201"), (11, "P-202"), (12, "P-203"),
    (13, "P-204"), (14, "P-205"), (15, "P-206"), (16, "P-207"),
    (17, "P-208"), (18, "P-209"),
]


def collect_ten_pid_evidence(
    source: Path, out: Path, *, ocr_pages: set[int] | None = None
) -> dict[str, Any]:
    """Run actual extraction and create unannotated source-linked review tasks.

    OCR is optional and limited by caller to avoid expensive P&ID-wide scans.
    """
    raw = source.read_bytes()
    preflight = preflight_pdf(raw, source.name)
    if preflight["page_count"] < 18:
        raise ValueError("10-sheet Pāhala benchmark requires 18 or more pages")
    original_sha = hashlib.sha256(raw).hexdigest()
    sheets: list[dict] = []
    tasks = []
    ocr_pages = ocr_pages or set()
    for page_num, expected_drawing in SHEETS:
        sheet = preflight["pages"][page_num - 1]
        data = extract_single_page(raw, page_num)
        _, result = build_pid_extraction(
            data, f"pahala_{expected_drawing}_p{page_num}.pdf",
            ocr=(page_num in ocr_pages),
        )
        counted = {
            "source_page": page_num, "drawing_number_from_official_index": expected_drawing,
            "source_sha256": original_sha,
            "isolated_page_sha256": result["document_sha256"],
            "source_pdf_page": page_num,
            "engineer_source_role_review": "not_performed",
            "page_preflight_role": sheet["role"],
            "native_text_available": sheet["has_native_text"],
            "ocr_attempted": page_num in ocr_pages,
            "tag_candidates": len(result["candidates"]),
            "native_tag_candidates": sum(
                c.get("source_method") == "native_pdf_text"
                for c in result["candidates"]
            ),
            "ocr_tag_candidates": sum(
                c.get("source_method", "").startswith("local_tesseract")
                for c in result["candidates"]
            ),
            "visual_matches": sum(
                bool(s.get("geometry_id")) for s in result["symbol_hypotheses"]
            ),
            "process_edge_proposals": sum(
                e.get("type") == "process_candidate"
                for e in result["connection_proposals"]
            ),
            "instrument_tap_proposals": sum(
                e.get("type") == "instrument_tap_candidate"
                for e in result["connection_proposals"]
            ),
            "unresolved_tees": len(result["unresolved_tees"]),
            "verified_equipment": 0,
            "verified_connections": 0,
            "accuracy_measured": False,
            "review_required": True,
            "warnings": result["warnings"][:20],
        }
        sheets.append(counted)
        tasks.append({
            "source_pdf_sha256": original_sha, "source_pdf_page": page_num,
            "expected_drawing_index_number": expected_drawing,
            "annotation_status": "EMPTY_REQUIRES_INDEPENDENT_ENGINEER_GOLD",
            "source_reference": {
                "original_name": source.name, "source_page": page_num,
            },
            "source_image_coordinates": "PDF points, top-left",
            "confirmed_tags": [],
            "confirmed_symbol_boxes": [],
            "confirmed_connections": [],
            "annotator": None,
            "independent_second_reviewer": None,
            "notes": "",
        })
    summary = {
        "corpus": "Pāhala public 25-page engineering drawing package",
        "license": "publicly accessible reference; do not redistribute engineering consultant drawings",
        "source_url": (
            "https://www.epa.gov/system/files/documents/2021-08/"
            "pahala-wwtp-design-build-drawings-2021-07-23.pdf"
        ),
        "original_sha256": original_sha,
        "official_drawing_index": {str(page): ref for page, ref in SHEETS},
        "legend_pages": [6, 7, 8],
        "extracted_pid_pages": len(sheets),
        "total_tag_candidates": sum(s["tag_candidates"] for s in sheets),
        "total_process_edge_proposals": sum(s["process_edge_proposals"] for s in sheets),
        "total_visual_matches": sum(s["visual_matches"] for s in sheets),
        "per_sheet": sheets,
        "gold_label_status": "not_collected",
        "performance_metrics": "NOT_AVAILABLE_UNTIL_ENGINEERS_ANNOTATE",
        "process_baseline_published": False,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "ten_sheet_extraction.json").write_text(json.dumps(summary, indent=2))
    (out / "engineer_gold_annotation_tasks.json").write_text(
        json.dumps({"source_sha256": original_sha, "tasks": tasks}, indent=2)
    )
    with (out / "ten_sheet_intake.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_page", "drawing_number_from_official_index",
            "page_preflight_role", "native_text_available",
            "tag_candidates", "ocr_tag_candidates", "visual_matches",
            "process_edge_proposals", "unresolved_tees", "accuracy_measured"
        ])
        writer.writeheader()
        for row in sheets:
            writer.writerow({k: row[k] for k in writer.fieldnames})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ocr-pages", type=int, nargs="*", default=[],
                        help="Optional original PDF page numbers to OCR")
    args = parser.parse_args()
    if not set(args.ocr_pages).issubset({p for p, _ in SHEETS}):
        parser.error("OCR pages must belong to the 10-page benchmark selection")
    report = collect_ten_pid_evidence(
        args.source, args.out, ocr_pages=set(args.ocr_pages)
    )
    print(json.dumps({
        "pages_processed": report["extracted_pid_pages"],
        "tags": report["total_tag_candidates"],
        "visual_matches": report["total_visual_matches"],
        "process_edge_proposals": report["total_process_edge_proposals"],
        "gold": report["gold_label_status"],
        "source_sha256": report["original_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
