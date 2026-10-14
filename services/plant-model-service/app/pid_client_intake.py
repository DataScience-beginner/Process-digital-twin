"""Conservative client drawing-set preflight and project legend dictionary.

A document package may contain an index, several legend sheets, P&IDs and
unrelated civil/structural pages. NEVER treat one uploaded PDF as one P&ID.
This is an intake/classification stage only; it does not approve graph data.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any

import fitz

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_PAGES = 80
MAX_LEGEND_EXAMPLES = 150

# Useful starting list; a real client project legend overrides ALL defaults.
P_AND_ID_TERMS = (
    "GATE VALVE", "GLOBE VALVE", "BALL VALVE", "CHECK VALVE",
    "BUTTERFLY VALVE", "CONTROL VALVE", "SOLENOID VALVE",
    "PRESSURE RELIEF VALVE", "PRESSURE SAFETY VALVE", "VACUUM RELIEF VALVE",
    "MOTOR OPERATED VALVE", "DIAPHRAGM VALVE", "THREE WAY VALVE",
    "FLOW METER", "MAGNETIC FLOWMETER", "CORIOLIS FLOW ELEMENT",
    "PRESSURE TRANSMITTER", "LEVEL TRANSMITTER", "TEMPERATURE ELEMENT",
    "VENT", "DRAIN", "STRAINER", "PIPELINE FILTER", "REDUCER",
    "PUMP, CENTRIFUGAL", "PUMP, DIAPHRAGM", "PUMP, SUBMERSIBLE",
    "COMPRESSOR", "BLOWER", "HEAT EXCHANGER", "VESSEL",
    "PROCESS LINES", "INSTRUMENT SIGNAL LINES",
    "ELECTRICAL SIGNAL", "SOFTWARE OR DATA LINK", "PRIMARY ELEMENT",
    "OFF PAGE CONNECTOR", "PIPELINE IDENTIFICATION",
)
_DRAWING_NUM = re.compile(
    r"\b(?:P|PI|PID|D)[-– ](?:\d{2,5}|[A-Z]{1,3}-\d{2,5})(?:[-–]\d{1,3})?\b",
    re.I,
)


def _text(page) -> str:
    return " ".join(page.get_text("text").split())


def _page_role(text: str, title_area: str, index: int) -> tuple[str, list[str]]:
    """Conservative classification; pages may be manually overridden later."""
    upper, title = text.upper(), title_area.upper()
    reasons = []
    if "DRAWING INDEX" in upper and index == 1:
        return "index", ["drawing index"]
    legend_hit = any(x in title for x in (
        "LEGENDS", "P&ID LEGEND", "P & ID LEGEND",
        "ABBREVIATIONS AND SYMBOLS", "LEGEND & GENERAL NOTES",
    ))
    legend_body = (
        ("SYMBOLS" in upper and "VALVES" in upper and "INSTRUMENT" in upper)
        or ("INSTRUMENT SIGNAL LINES" in upper and "FUNCTIONAL IDENTIFICATION" in upper)
        or ("LEGENDS, ABBREV" in upper)
    )
    if legend_hit or legend_body:
        return "legend", ["legend sheet title/technical symbol table"]
    if "P&ID" in title or "P & ID" in title or "PIPING AND INSTRUMENTATION" in title:
        return "pid", ["P&ID title block"]
    # Some client drawing title blocks list only sheet number P-123.
    number = _DRAWING_NUM.search(title)
    if number and "LEGEND" not in title and (
        "P&ID" in upper or "PROCESS" in upper or "SIGNAL" in upper
    ):
        return "pid_candidate", ["P-series drawing and process context"]
    if "CIVIL" in title or "SITE PLAN" in title:
        return "context", ["civil/site drawing"]
    if index == 1 and ("PROJECT" in upper or "INDEX" in upper):
        return "index_candidate", ["front sheet"]
    return "unknown", ["manual document type review required"]


def _legend_candidates(page, original_sha: str, page_number: int) -> list[dict]:
    """Find engineering terms with exact PDF-space evidence, NOT symbol labels.

    The term near a symbol is a potential dictionary entry. Its graphic must be
    independently cropped/matched and reviewed before model training.
    """
    matches = []
    for term in P_AND_ID_TERMS:
        for box in page.search_for(term, quads=False)[:5]:
            # Suggest a left-adjacent crop for operator inspection only.
            # Client legend layouts vary; this is NOT a verified symbol box.
            crop = [
                round(max(0, box.x0 - 105), 2),
                round(max(0, box.y0 - 12), 2),
                round(max(0, box.x0 - 4), 2),
                round(min(page.rect.height, box.y1 + 12), 2),
            ]
            evidence_id = hashlib.sha256(
                f"{original_sha}:{page_number}:{term}:{list(box)}".encode()
            ).hexdigest()[:20]
            matches.append({
                "id": "LEGEND-" + evidence_id,
                "label": term,
                "page": page_number,
                "source_pdf_sha256": original_sha,
                "bbox": [round(v, 2) for v in box],
                "evidence_type": "legend_text_not_symbol_annotation",
                "proposed_symbol_crop_pdf": crop,
                "proposed_crop_status": "unreviewed_geometric_guess",
                "review_status": "unreviewed",
            })
            if len(matches) >= MAX_LEGEND_EXAMPLES:
                return matches
    return matches


def preflight_pdf(content: bytes, filename: str) -> dict[str, Any]:
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"{filename}: exceeds 20 MB per-file limit")
    if not content.startswith(b"%PDF-"):
        raise ValueError(f"{filename}: invalid PDF signature")
    sha = hashlib.sha256(content).hexdigest()
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"{filename}: invalid PDF") from exc
    try:
        if pdf.needs_pass:
            raise ValueError(f"{filename}: protected PDF needs manual handling")
        if pdf.page_count > MAX_DOCUMENT_PAGES:
            raise ValueError(f"{filename}: too many pages for prototype")
        pages, legends = [], []
        for number, page in enumerate(pdf, start=1):
            rect = page.rect
            all_text = _text(page)
            # Right-side 28% captures common title blocks including Pāhala's
            # right-edge drawing number, without guessing company standards.
            title_text = " ".join(page.get_text(
                "text",
                clip=fitz.Rect(rect.x0 + rect.width * .70,
                               rect.y0 + rect.height * .40,
                               rect.x1, rect.y1)
            ).split())
            role, reasons = _page_role(all_text, title_text, number)
            ids = sorted(set(x.upper().replace(" ", "-")
                             for x in _DRAWING_NUM.findall(title_text)))
            text_words = len(all_text.split())
            pages.append({
                "page": number, "role": role, "classification_reasons": reasons,
                "drawing_numbers": ids[:8],
                "has_native_text": text_words > 10,
                "native_word_count": text_words,
                "width_pts": round(rect.width, 2),
                "height_pts": round(rect.height, 2),
                "source_bbox_coordinate_space": "PDF points, top-left",
                "role_review_status": "unreviewed",
            })
            if role == "legend":
                legends.extend(_legend_candidates(page, sha, number))
        types = dict(Counter(p["role"] for p in pages))
        return {
            "filename": filename, "source_sha256": sha,
            "page_count": pdf.page_count, "role_counts": types,
            "pages": pages, "legend_terms": legends,
            "requires_legend_review": any(p["role"] == "legend" for p in pages),
            "unknown_page_count": sum(p["role"] in ("unknown","index_candidate")
                                      for p in pages),
            "pipeline_status": "preflight_only_no_graph",
            "provenance_status": "source_pdf_sha256_and_source_page_retained",
        }
    finally:
        pdf.close()


def extract_single_page(content: bytes, page_number: int) -> bytes:
    """Copy an original sheet into an isolated PDF for existing vision pipeline."""
    with fitz.open(stream=content, filetype="pdf") as source:
        if page_number < 1 or page_number > len(source):
            raise ValueError("Page number outside source")
        output = fitz.open()
        try:
            output.insert_pdf(source, from_page=page_number-1, to_page=page_number-1)
            return output.tobytes(garbage=4, deflate=True)
        finally:
            output.close()
