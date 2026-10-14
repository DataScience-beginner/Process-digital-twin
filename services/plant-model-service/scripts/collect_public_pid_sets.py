"""Download public P&ID drawing packages *locally* for internal benchmarking.

The documents are public government references, but consultant copyright may
still apply. Never copy the original PDFs into the git repo or CI artifacts.
Report only derived sheet classifications, hashes and extraction counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

from app.pid_client_intake import MAX_DOCUMENT_BYTES, preflight_pdf

SOURCES = {
    "pahala": {
        "url": "https://www.epa.gov/system/files/documents/2021-08/pahala-wwtp-design-build-drawings-2021-07-23.pdf",
        "name": "Pahala_WWTP_25_sheet_PIDs_with_3_legends.pdf",
        "publisher": "US EPA public document hosting / County of Hawaii drawings",
        "expect_legend": True,
        "expect_pid": True,
        "notes": "25-page public drawing set, sheet 6-8 P-001/P-002/P-003 legends, 9-25 process P&IDs. Existing drawing states concept only.",
        "license": "public access only; engineering consultant copyright not cleared",
    },
    "virden": {
        "url": "https://www.gov.mb.ca/sd/eal/registries/5697virden/2019-04-26_5697_00_phase_2_p_and_i_drwngs.pdf",
        "name": "Virden_WWTF_Scanned_Drawing_Set.pdf",
        "publisher": "Province of Manitoba public environment registry",
        "expect_legend": False,
        "expect_pid": True,
        "notes": "Scanned process plant drawings, independently sourced; specific legend status unverified.",
        "license": "public access only, reuse not cleared",
    },
    "mckinleyville": {
        "url": "https://www.mckinleyvillecsd.ca.gov/files/92cf028f6/MCSD%2B4.5%2BMG%2BReservoir%2BDrawings%2B-%2BBid%2BSet%2B-%2BFebruary%2B2023.pdf",
        "name": "McKinleyville_57_sheet_public_bid_drawings.pdf",
        "publisher": "McKinleyville Community Services District",
        "expect_legend": True,
        "expect_pid": True,
        "notes": "Includes drawing I-01: P&ID Legend and Abbreviations, reported as sheet 54 of 57.",
        "license": "public access only; consultant design ownership not cleared",
    },
    "lanl_legend": {
        "url": "https://engstandards.lanl.gov/drawings_details/IC_pdf/ST6999-M0002-R2.pdf",
        "name": "LANL_ST6999_M0002_legend.pdf",
        "publisher": "Los Alamos National Laboratory Engineering Standards",
        "expect_legend": True,
        "expect_pid": False,
        "notes": "A distinct standard legend for valve/instrument letter designators.",
        "license": "public standards drawing, terms must be verified before redistribution",
    },
}


def download_pinned(source_id: str) -> bytes:
    meta = SOURCES[source_id]
    request = Request(meta["url"], headers={
        "User-Agent": "Digital-BDEP-PID-Engineering-Evaluation/1.0"
    })
    with urlopen(request, timeout=65) as handle:
        content = handle.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("Over 20 MB document input limit")
    if not content.startswith(b"%PDF-"):
        raise ValueError("Publisher returned non-PDF document")
    return content


def run_collection(out: Path, ids: list[str], *, save_originals: bool = False,
                   analyze_one: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "purpose": "Real public P&ID sets with legends: client intake proof-of-concept",
        "publication_policy": "Do not redistribute original consultant-created PDFs.",
        "source_documents": [],
        "failed_downloads": [],
        "originals_saved_in_local_workspace": save_originals,
        "training_approved": False,
    }
    for source_id in ids:
        if source_id not in SOURCES:
            raise ValueError(f"Source {source_id} is not allowlisted")
        meta = SOURCES[source_id]
        started = time.monotonic()
        try:
            content = download_pinned(source_id)
            inventory = preflight_pdf(content, meta["name"])
            if save_originals:
                (out / meta["name"]).write_bytes(content)
            entry = {
                "id": source_id, "publisher": meta["publisher"],
                "source_url": meta["url"],
                "source_sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
                "page_count": inventory["page_count"],
                "role_counts": inventory["role_counts"],
                "sheet_inventory": [
                    {"page": page["page"], "role": page["role"],
                     "drawing_numbers": page["drawing_numbers"],
                     "has_native_text": page["has_native_text"]}
                    for page in inventory["pages"]
                ],
                "legend_candidate_terms": len(inventory["legend_terms"]),
                "legend_candidate_examples": inventory["legend_terms"][:20],
                "verification": "roles_are_heuristic_needs_engineer_review",
                "notes": meta["notes"], "license_review": meta["license"],
                "elapsed_seconds": round(time.monotonic()-started, 2),
            }
            if analyze_one:
                pid_page = next(
                    (p["page"] for p in inventory["pages"]
                     if p["role"] in ("pid","pid_candidate")),
                    None,
                )
                if pid_page:
                    from app.pid_client_intake import extract_single_page
                    from app.pid_pipeline import build_pid_extraction
                    sheet_data = extract_single_page(content, pid_page)
                    _, extraction = build_pid_extraction(
                        sheet_data, f"{source_id}-sheet-{pid_page}.pdf",
                        ocr=False,
                    )
                    entry["unreviewed_pipeline_sample"] = {
                        "page": pid_page,
                        "tag_candidates": len(extraction["candidates"]),
                        "geometry_matched_symbols": sum(
                            bool(s.get("geometry_id"))
                            for s in extraction["symbol_hypotheses"]
                        ),
                        "process_graph_proposals": len(
                            extraction["connection_proposals"]
                        ),
                        "source_trace": bool(
                            extraction.get("document_sha256")
                        ),
                        "correctness_unknown": True,
                    }
            report["source_documents"].append(entry)
        except Exception as exc:
            report["failed_downloads"].append({
                "id": source_id, "url": meta["url"],
                "reason": f"{type(exc).__name__}: {str(exc)[:260]}",
            })
    (out / "public_pid_intake_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path("data/pid_corpus/external/client_sets"))
    parser.add_argument("--sources", nargs="+", choices=list(SOURCES),
                        default=list(SOURCES))
    parser.add_argument("--save-originals", action="store_true",
                        help="Keep PDFs only on your permitted LOCAL machine.")
    parser.add_argument("--analyze-one", action="store_true",
                        help="Run existing model on first possible P&ID page.")
    args = parser.parse_args()
    report = run_collection(args.out, args.sources,
                            save_originals=args.save_originals,
                            analyze_one=args.analyze_one)
    print(json.dumps({
        "downloaded": [x["id"] for x in report["source_documents"]],
        "failed": report["failed_downloads"],
        "summary": [
            {"id": x["id"], "pages": x["page_count"],
             "roles": x["role_counts"],
             "legend_terms": x["legend_candidate_terms"],
             "sample": x.get("unreviewed_pipeline_sample")}
            for x in report["source_documents"]
        ],
    }, indent=2))
    if not any(x["id"] == "pahala" for x in report["source_documents"]):
        raise SystemExit("Required Pahala legend+P&ID source was not retrievable")


if __name__ == "__main__":
    main()
