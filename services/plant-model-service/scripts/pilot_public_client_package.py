"""Exercise real public 25-sheet Pāhala set through the same client browser API.

Input is downloaded locally by collect_public_pid_sets.py --save-originals.
Do not archive or publish the original PDF; export source-cited metrics only.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def run_pilot(source: Path, working: Path) -> dict:
    from fastapi.testclient import TestClient
    from app.main import app

    working.mkdir(parents=True, exist_ok=True)
    body = source.read_bytes()
    with TestClient(app) as client:
        intake = client.post(
            "/api/pid-digitization/client-batches",
            data={
                "client_label": "Public EPA documentation / demonstration",
                "package_label": "Pahala WWTP legend + P&ID engineering intake",
            },
            files={"files": (source.name, body, "application/pdf")},
        )
        assert intake.status_code == 200, intake.text
        package = intake.json()
        document = package["documents"][0]
        pages = document["preflight"]["pages"]
        legends = [p for p in pages if p["role"] == "legend"]
        pids = [p for p in pages if p["role"] == "pid"]
        assert len(legends) >= 3, f"Expected 3 legend sheets, found {len(legends)}"
        assert pids, "No P&ID pages found"

        # An engineer has to inspect actual sheets for correct assignment.
        # This scripted test ONLY SIMULATES role acceptance for API testing.
        roles = [
            {"document_id": document["id"], "page": p["page"],
             "role": "legend"} for p in legends
        ]
        roles.append({"document_id": document["id"],
                      "page": pids[0]["page"], "role": "pid"})
        response = client.post(
            f'/api/pid-digitization/client-batches/{package["id"]}/roles/review',
            json={"reviewer": "AUTOMATED_TEST_NOT_ENGINEERING_APPROVAL",
                  "decisions": roles},
        )
        assert response.status_code == 200, response.text
        confirmed = response.json()["readiness"]
        assert confirmed["readiness"] == "ready_for_pagewise_evidence_extraction"

        first_term = next(iter(document["preflight"]["legend_terms"]), None)
        sample_preview = None
        if first_term is not None:
            cropped = client.get(
                f'/api/pid-digitization/client-batches/{package["id"]}/documents/'
                f'{document["id"]}/legends/{first_term["id"]}.png'
            )
            sample_preview = cropped.status_code == 200
            # Never automatically approve an uninspected visual crop.
            assert sample_preview

        pid_number = pids[0]["page"]
        analysis = client.post(
            f'/api/pid-digitization/client-batches/{package["id"]}/documents/'
            f'{document["id"]}/pages/{pid_number}/analyze'
        )
        assert analysis.status_code == 200, analysis.text
        result = analysis.json()
        detailed = client.get(
            f'/api/pid-digitization/imports/{result["import_id"]}'
        )
        assert detailed.status_code == 200, detailed.text
        record = detailed.json()
        assert record["client_source"]["source_original_page"] == pid_number
        assert record["client_source"]["source_original_sha256"] == document[
            "preflight"]["source_sha256"]
        assert record["review_required"] is True
        assert result["publish_ready"] is False

        report = {
            "input": "real Pahala 25-sheet public PDF",
            "publisher": "US EPA public hosting / County of Hawaii",
            "source_url": "https://www.epa.gov/system/files/documents/2021-08/pahala-wwtp-design-build-drawings-2021-07-23.pdf",
            "source_sha256": document["preflight"]["source_sha256"],
            "sheets_in_set": document["preflight"]["page_count"],
            "legend_sheets_identified": len(legends),
            "pid_sheets_identified": len(pids),
            "client_package_created": True,
            "source_legend_crop_preview_available": sample_preview,
            "role_review_simulated": True,
            "reviewer_is_real_engineer": False,
            "sample_pid_page": pid_number,
            "sample_tag_candidates": result["tag_candidates"],
            "sample_symbol_hypotheses": result["symbol_candidates"],
            "sample_graph_proposals": result["connection_candidates"],
            "source_trace_preserved": True,
            "engineering_publish_ready": False,
            "benchmark_accuracy_computed": False,
            "visual_review_required": True,
        }
        (working / "public_client_e2e_report.json").write_text(
            json.dumps(report, indent=2)
        )
        return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    os.environ["DATABASE_URL"] = (
        "sqlite+pysqlite:///" + str((args.out/"public_pid_demo.sqlite").resolve())
    )
    os.environ["BDEP_PID_STORAGE"] = str(args.out / "uploaded_sources")
    print(json.dumps(run_pilot(args.source, args.out), indent=2))


if __name__ == "__main__":
    main()
