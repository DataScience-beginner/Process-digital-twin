"""Regression coverage for input normalization, symbol evidence and graph review."""
import json
import shutil
from pathlib import Path

import fitz
import pytest

from app.models import PlantModel
from app.pid_digitization import accepted_plant_draft
from app.pid_pipeline import build_pid_extraction, normalize_pid_input
from scripts.generate_pid_corpus import generate


@pytest.fixture
def corpus(tmp_path):
    generate(tmp_path)
    return tmp_path


def test_all_supported_input_forms_normalize_and_preflight(corpus):
    for name in ("baseline.pdf", "complex.pdf", "multisheet.pdf",
                 "scanned.pdf", "raster.png", "compressed.jpg"):
        normalized, result = build_pid_extraction(
            (corpus / name).read_bytes(), name, ocr=False
        )
        assert normalized[:5] == b"%PDF-"
        assert result["page_count"] == (2 if name == "multisheet.pdf" else 1)
        assert result["input"]["source_sha256"]
        assert result["pipeline"]["engineer_review"] == "required"
    _, scanned = build_pid_extraction(
        (corpus / "scanned.pdf").read_bytes(), "scanned.pdf"
    )
    assert not scanned["candidates"]  # local OCR disabled


def test_vector_symbol_and_direct_line_evidence_has_pdf_provenance(corpus):
    _, result = build_pid_extraction(
        (corpus / "baseline.pdf").read_bytes(), "baseline.pdf"
    )
    tags = {c["tag"] for c in result["candidates"]}
    assert {"V-101", "P-101", "FCV-101", "PSV-101", "PT-101"} <= tags
    by_tag = {item["tag"]: item for item in result["symbol_hypotheses"]}
    for tag in ("V-101", "P-101", "FCV-101", "PT-101"):
        assert by_tag[tag]["geometry_id"] is not None, tag
        assert by_tag[tag]["bbox"]
    process_edges = {
        frozenset((e["tag_a"], e["tag_b"]))
        for e in result["connection_proposals"]
        if e["type"] == "process_candidate"
    }
    assert frozenset(("V-101", "FCV-101")) in process_edges
    assert frozenset(("FCV-101", "P-101")) in process_edges
    assert all(edge["review_status"] == "unreviewed"
               for edge in result["connection_proposals"])
    assert all(edge["source_segment_ids"] for edge in result["connection_proposals"])


def test_no_graph_connections_without_explicit_engineering_review(corpus):
    _, result = build_pid_extraction((corpus / "baseline.pdf").read_bytes(), "baseline.pdf")
    for candidate in result["candidates"]:
        candidate["review_status"] = "accepted"
    draft = accepted_plant_draft(
        "IMPORT", "BDEP-DEMO-004", result["candidates"], result["connection_proposals"]
    )
    assert draft["plant_model"]["connections"] == []
    assert not draft["publish_ready"]


def test_accepted_sourced_graph_validates_as_real_bdep_plant_model(corpus):
    _, result = build_pid_extraction((corpus / "baseline.pdf").read_bytes(), "baseline.pdf")
    for candidate in result["candidates"]:
        candidate["review_status"] = "accepted"
    links = result["connection_proposals"]
    for edge in links:
        if edge["type"] == "process_candidate" and frozenset(
            (edge["tag_a"], edge["tag_b"])
        ) in (frozenset(("V-101","FCV-101")),frozenset(("FCV-101","P-101"))):
            edge.update(
                review_status="accepted", direction="a_to_b", reviewed_by="engineer"
            )
    draft = accepted_plant_draft(
        "IMPORT", "BDEP-DEMO-004", result["candidates"], links
    )
    assert len(draft["plant_model"]["connections"]) >= 2
    model = PlantModel.model_validate(draft["plant_model"])
    assert model.connections
    assert len(draft["edge_source_evidence"]) >= 2
    assert draft["publish_ready"] is False


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="local tesseract not installed")
def test_scanned_pdf_ocr_option(corpus):
    pytest.importorskip("pytesseract")
    _, output = build_pid_extraction(
        (corpus / "scanned.pdf").read_bytes(), "scanned.pdf", ocr=True
    )
    assert output["pipeline"]["ocr"] == "attempted"
    assert output["candidates"], "OCR should identify at least one synthetic tag"
