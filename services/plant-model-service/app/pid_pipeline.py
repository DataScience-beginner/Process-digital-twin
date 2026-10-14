"""Input normalization + multiple evidence stages for the brownfield P&ID lane.

Native raster images are normalized to a PDF page with a documented coordinate
transform. OCR runs locally only when explicitly enabled, if Tesseract exists.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from .pid_digitization import (
    MAX_PDF_BYTES, MAX_CANDIDATES, TAG_PATTERN, _kind, extract_pid_pdf,
)
from .pid_geometry import (
    detect_symbol_hypotheses, extract_vector_evidence, propose_connections,
)
from .pid_raster_geometry import extract_raster_evidence
from .pid_network import propose_network_connections
from .pid_junctions import propose_unresolved_tees


def normalize_pid_input(raw: bytes, filename: str) -> tuple[bytes, dict[str, Any]]:
    """Convert a supported local source to PDF with traceable source metadata."""
    if len(raw) > MAX_PDF_BYTES:
        raise ValueError("Input exceeds 20 MB")
    source_sha256 = hashlib.sha256(raw).hexdigest()
    ext = Path(filename).suffix.lower()
    if ext == ".pdf" and raw.startswith(b"%PDF-"):
        return raw, {
            "source_format": "pdf",
            "source_sha256": source_sha256,
            "coordinate_system": "pdf_points_top_left",
            "normalization": "none",
        }
    if ext not in (".png", ".jpg", ".jpeg"):
        raise ValueError("Supported source formats: PDF, PNG, JPG/JPEG")
    try:
        Image.MAX_IMAGE_PIXELS = 30_000_000
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            if width * height > 30_000_000:
                raise ValueError("Raster image exceeds 30 megapixels")
            buffer = io.BytesIO()
            rgb.save(buffer, format="PNG")
            image_png = buffer.getvalue()
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Image could not be safely decoded") from exc
    document = fitz.open()
    try:
        page = document.new_page(width=width * .75, height=height * .75)
        page.insert_image(page.rect, stream=image_png)
        content = document.tobytes(garbage=4, deflate=True)
    finally:
        document.close()
    return content, {
        "source_format": "raster_image",
        "source_sha256": source_sha256,
        "coordinate_system": "pdf_points_top_left",
        "normalization": "image embedded into PDF at 72/96 point-per-pixel",
        "original_pixel_dimensions": [width, height],
        "pixels_per_pdf_point": 4/3,
    }


def _ocr_empty_pages(pdf: bytes, existing: list[dict], page_meta: list[dict]) -> tuple[list[dict], list[str]]:
    warnings = []
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        return [], ["OCR requested but optional pytesseract package not installed"]
    candidates = []
    sha = hashlib.sha256(pdf).hexdigest()
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        for page_idx, page in enumerate(doc):
            if page_meta[page_idx]["has_text"]:
                continue
            try:
                factor = 2
                pix = page.get_pixmap(matrix=fitz.Matrix(factor, factor), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                result = pytesseract.image_to_data(
                    image, output_type=Output.DICT, config="--psm 11"
                )
            except Exception as exc:
                warnings.append(f"Page {page_idx + 1}: local OCR unavailable ({type(exc).__name__})")
                continue
            lines = {}
            for i, term in enumerate(result["text"]):
                token = str(term).strip()
                if not token:
                    continue
                line_id = (result["block_num"][i], result["par_num"][i], result["line_num"][i])
                lines.setdefault(line_id, []).append(i)
            for indexes in lines.values():
                for pos, i in enumerate(indexes):
                    for grp in (indexes[pos:pos + 1], indexes[pos:pos + 2]):
                        if not grp:
                            continue
                        string = " ".join(str(result["text"][j]).strip() for j in grp)
                        match = TAG_PATTERN.fullmatch(string)
                        if not match:
                            continue
                        prefix, number = match.groups()
                        prefix = prefix.upper()
                        tag = f"{prefix}-{number.upper()}"
                        bounds = [
                            min(result["left"][j] for j in grp) / factor,
                            min(result["top"][j] for j in grp) / factor,
                            max(result["left"][j] + result["width"][j] for j in grp) / factor,
                            max(result["top"][j] + result["height"][j] for j in grp) / factor,
                        ]
                        bbox = [round(x, 2) for x in bounds]
                        category, object_type = _kind(prefix)
                        cid = hashlib.sha256(
                            f"{sha}:ocr:{page_idx + 1}:{tag}:{bbox}".encode()
                        ).hexdigest()[:16]
                        if all(c["id"] != cid for c in candidates):
                            candidates.append({
                                "id": cid, "tag": tag,
                                "category": category, "object_type": object_type,
                                "page": page_idx + 1, "bbox": bbox,
                                "source_text": string,
                                "review_status": "unreviewed",
                                "confidence": "ocr_candidate_unvalidated",
                                "source_method": "local_tesseract_ocr",
                            })
                    if len(candidates) >= MAX_CANDIDATES:
                        warnings.append("OCR candidate count limit reached")
                        return candidates, warnings
    return candidates, warnings


def build_pid_extraction(
    raw: bytes, filename: str, *, ocr: bool = False
) -> tuple[bytes, dict[str, Any]]:
    normalized_pdf, input_meta = normalize_pid_input(raw, filename)
    extracted = extract_pid_pdf(normalized_pdf)
    extracted["input"] = input_meta
    for tag in extracted["candidates"]:
        tag.setdefault("source_method", "native_pdf_text")
    if ocr:
        supplement, warnings = _ocr_empty_pages(
            normalized_pdf, extracted["candidates"], extracted["pages"]
        )
        extracted["candidates"].extend(supplement)
        extracted["warnings"].extend(warnings)
    vector = extract_vector_evidence(normalized_pdf)
    vector_pages = {p["page"] for p in vector["segments"] + vector["primitives"]}
    raster = extract_raster_evidence(normalized_pdf, vector_pages)
    geometry = {
        "primitives": vector["primitives"] + raster["primitives"],
        "segments": vector["segments"] + raster["segments"],
        "warnings": vector["warnings"] + raster["warnings"],
    }
    symbols = detect_symbol_hypotheses(extracted["candidates"], geometry["primitives"])
    network = propose_network_connections(symbols, geometry["segments"], extracted["document_sha256"])
    unresolved_tees = propose_unresolved_tees(geometry["segments"], extracted["document_sha256"])
    links = network["connection_proposals"]
    extracted["symbol_hypotheses"] = symbols
    extracted["connection_proposals"] = links
    extracted["network_diagnostics"] = network["diagnostics"]
    extracted["unresolved_tees"] = unresolved_tees
    extracted["network_diagnostics"]["unresolved_tees"] = len(unresolved_tees)
    extracted["vector_evidence"] = geometry
    extracted["warnings"].extend(geometry["warnings"])
    extracted["pipeline"] = {
        "input": "complete",
        "text": "complete",
        "ocr": "attempted" if ocr else "disabled",
        "vector_geometry": "complete",
        "raster_geometry": "attempted_offline_heuristics",
        "symbol_recognition": "tag_plus_geometric_hypotheses_only",
        "graph_reconstruction": "multi_segment_endpoint_graph_hypotheses",
        "engineer_review": "required",
        "digital_plant": "draft_only",
    }
    return normalized_pdf, extracted
