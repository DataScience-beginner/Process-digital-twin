"""Offline, source-traceable tag extraction from existing born-digital P&ID PDFs.

No piping connectivity, equipment properties, or technical approvals are inferred.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

import fitz

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PAGES = 80
MAX_CANDIDATES = 10000

_PREFIXES = (
    "PSV", "PRV", "FCV", "LCV", "PCV", "TCV", "SDV", "BDV", "MOV",
    "NRV", "XV", "FIC", "LIC", "PIC", "TIC", "PDIT", "DPIT",
    "PT", "PI", "FT", "FI", "LT", "LI", "TT", "TI", "P", "V", "E", "TK",
)
TAG_PATTERN = re.compile(
    rf"^({'|'.join(_PREFIXES)})[- ]?(\d{{2,5}}[A-Z]?)$", re.IGNORECASE
)
EQUIPMENT = {"P": "centrifugal_pump", "V": "vertical_separator"}
VALVES = {
    "PSV": "relief_valve", "PRV": "relief_valve", "FCV": "control_valve",
    "LCV": "control_valve", "PCV": "control_valve", "TCV": "control_valve",
    "SDV": "isolation_valve", "BDV": "isolation_valve", "MOV": "isolation_valve",
    "XV": "isolation_valve", "NRV": "check_valve",
}
INSTRUMENTS = {
    "PT": "pressure_transmitter", "PI": "pressure_indicator",
    "FT": "flow_transmitter", "LT": "level_transmitter",
    "LI": "level_indicator", "LIC": "level_controller",
    "FIC": "flow_controller",
}


def _kind(prefix: str) -> tuple[str, str | None]:
    if prefix in EQUIPMENT:
        return "equipment", EQUIPMENT[prefix]
    if prefix in VALVES:
        return "valve", VALVES[prefix]
    if prefix in INSTRUMENTS:
        return "instrument", INSTRUMENTS[prefix]
    return "unmapped", None


def _clean(word: str) -> str:
    return word.strip(".,:;()[]{}<>\"' ")


def _bbox(words: list[tuple]) -> list[float]:
    return [round(value, 2) for value in (
        min(w[0] for w in words), min(w[1] for w in words),
        max(w[2] for w in words), max(w[3] for w in words),
    )]


def extract_pid_pdf(content: bytes) -> dict[str, Any]:
    """Extract unapproved tag candidates with precise PDF coordinate evidence."""
    if len(content) > MAX_PDF_BYTES:
        raise ValueError("PDF exceeds the 20 MB initial import limit")
    if not content.startswith(b"%PDF-"):
        raise ValueError("Upload a valid PDF file")
    digest = hashlib.sha256(content).hexdigest()
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("PDF cannot be opened") from exc
    try:
        if doc.needs_pass:
            raise ValueError("Password-protected PDFs are not supported")
        if doc.page_count > MAX_PAGES:
            raise ValueError("PDF exceeds the 80-page initial import limit")
        candidates: list[dict[str, Any]] = []
        pages: list[dict[str, Any]] = []
        warnings: list[str] = []
        seen: set[tuple] = set()
        for page_index, page in enumerate(doc):
            words = page.get_text("words", sort=True)
            lines: dict[tuple[int, int], list[tuple]] = {}
            for word in words:
                lines.setdefault((int(word[5]), int(word[6])), []).append(word)
            for line_words in lines.values():
                line_words.sort(key=lambda word: (int(word[7]), word[0]))
                for i in range(len(line_words)):
                    for span in (line_words[i:i + 1], line_words[i:i + 2]):
                        raw = " ".join(_clean(word[4]) for word in span)
                        match = TAG_PATTERN.fullmatch(raw)
                        if not match:
                            continue
                        prefix, number = match.groups()
                        prefix = prefix.upper()
                        tag = f"{prefix}-{number.upper()}"
                        box = _bbox(span)
                        key = (page_index, tag, *box)
                        if key in seen:
                            continue
                        seen.add(key)
                        category, object_type = _kind(prefix)
                        source_id = hashlib.sha256(
                            f"{digest}:{page_index + 1}:{tag}:{box}".encode()
                        ).hexdigest()[:16]
                        candidates.append({
                            "id": source_id, "tag": tag, "category": category,
                            "object_type": object_type, "page": page_index + 1,
                            "bbox": box, "source_text": raw,
                            "review_status": "unreviewed",
                            "confidence": "candidate_not_validated",
                        })
                        if len(candidates) >= MAX_CANDIDATES:
                            warnings.append("Candidate limit reached; split input into smaller batches")
                            break
                    if len(candidates) >= MAX_CANDIDATES:
                        break
                if len(candidates) >= MAX_CANDIDATES:
                    break
            if not words:
                warnings.append(
                    f"Page {page_index + 1} has no extractable text; scanned-page OCR is not implemented"
                )
            pages.append({
                "page": page_index + 1,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "has_text": bool(words),
                "vector_path_count": len(page.get_drawings()) if words else 0,
            })
            if len(candidates) >= MAX_CANDIDATES:
                break
        return {
            "document_sha256": digest,
            "page_count": doc.page_count,
            "pages": pages,
            "candidates": candidates,
            "warnings": warnings,
            "extraction_scope": "vector_text_tags_only",
            "topology_status": "not_reconstructed",
            "review_required": True,
        }
    finally:
        doc.close()


def accepted_plant_draft(import_id: str, project_id: str, candidates: list[dict]) -> dict:
    """Map reviewed tag identities into a disconnected draft PlantModel.

    The draft is NEVER publication-ready until real connections/properties are verified.
    """
    by_tag: dict[str, list[dict]] = {}
    for candidate in candidates:
        if candidate["review_status"] == "accepted":
            by_tag.setdefault(candidate["tag"], []).append(candidate)
    objects: list[dict] = []
    unmapped: list[str] = []
    for tag, mentions in sorted(by_tag.items()):
        candidate = mentions[0]
        category, object_type = candidate["category"], candidate["object_type"]
        if category == "unmapped" or object_type is None:
            unmapped.append(tag)
            continue
        type_key = {
            "equipment": "equipment_type",
            "valve": "valve_type",
            "instrument": "instrument_type",
        }[category]
        objects.append({
            "id": f"PID-{category.upper()}-{tag}",
            "tag": tag,
            "category": category,
            type_key: object_type,
            "service": None,
            "ports": [],
            "properties": {
                "source_import_id": import_id,
                "source_page": mentions[0]["page"],
                "source_mentions": len(mentions),
                "verification": "tag_only_reviewed",
            },
        })
    return {
        "plant_model": {
            "project_id": project_id,
            "objects": objects,
            "connections": [],
            "associations": [],
            "modules": [],
        },
        "unmapped_accepted_tags": unmapped,
        "topology_status": "not_reconstructed",
        "publish_ready": False,
        "reason": "Only tag identities verified; physical connectivity and properties remain unverified",
    }
