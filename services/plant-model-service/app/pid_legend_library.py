"""Fail-closed, source-traceable legend library builder.

Engineering rules:
* A graphic without a verified adjacent written legend description is not a symbol class.
* Rotations/crops are not independent training samples or accuracy measurements.
* A candidate cannot become an approved training symbol without TWO distinct reviewers.
* Missing/unmapped legend sheets prevent the library-wide ready flag.
* Client PDFs, source images and filled-in annotations stay OUT of public GitHub.

Bounding boxes use PyMuPDF's displayed `page.rect` PDF-point coordinate space,
with 1-based page numbers.  Page renders are made using `get_pixmap(clip=...)`
so the graphic and label crops share that same coordinate system.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

SCHEMA = "pid-legend-library-v1"
CLASS_STATUSES = {"proposed", "needs_review", "approved", "rejected"}
PAGE_ROLES = {"symbol_legend", "line_legend", "instrument_legend", "typical_detail", "abbreviation", "mixed_legend"}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalize_bbox(bbox: Any, page: fitz.Page, what: str) -> list[float]:
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError(f"{what}: bbox must have 4 PDF-point values")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in bbox):
        raise ValueError(f"{what}: bbox coordinates must be numeric")
    x0, y0, x1, y1 = [float(v) for v in bbox]
    if not (0 <= x0 < x1 <= page.rect.width and 0 <= y0 < y1 <= page.rect.height):
        raise ValueError(f"{what}: bbox outside displayed PDF page {page.rect}")
    if x1 - x0 < 2 or y1 - y0 < 2:
        raise ValueError(f"{what}: box smaller than 2 points")
    return [round(x, 3) for x in (x0, y0, x1, y1)]


def _area_of_intersection(a: list[float], b: list[float]) -> float:
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def _crop(page: fitz.Page, bbox: list[float], *, scale: float = 3.0) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=fitz.Rect(bbox), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def create_inventory(pdf_bytes: bytes, legend_page_numbers: list[int], *, source_name: str) -> dict[str, Any]:
    if not pdf_bytes or not legend_page_numbers:
        raise ValueError("Supply nonempty PDF bytes and explicit proposed legend pages")
    if len(set(legend_page_numbers)) != len(legend_page_numbers):
        raise ValueError("Duplicate legend page in inventory")
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        pages = []
        for n in legend_page_numbers:
            if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= len(pdf):
                raise ValueError(f"Legend page {n} not in source PDF")
            pg = pdf[n - 1]
            pages.append({
                "page_1based": n,
                "page_dimensions_display_pdf_pt": [round(pg.rect.width, 2), round(pg.rect.height, 2)],
                "page_rotation_deg": pg.rotation,
                "role": "mixed_legend",
                "reviewed_complete": False,
                "expected_symbol_items": None,
                "notes": "Await engineer inventory; some sheets are typical details rather than individual glyphs",
            })
    return {
        "schema": SCHEMA,
        "source_name": source_name,
        "source_sha256": sha256(pdf_bytes),
        "coordinate_system": "displayed PDF points; 1-based page; PyMuPDF page.rect/get_pixmap(clip)",
        "pages": pages,
        "symbols": [],
        "library_readiness": "NOT_READY",
        "rights": "Source is private/restricted. Do not commit client scans/annotations to public repository.",
    }


def compile_library(pdf_bytes: bytes, manifest: dict[str, Any], output_folder: Path,
                    *, scale: float = 3.0) -> dict[str, Any]:
    """Generate private review cutouts; only reviewed records enter approved library.

    Writes approved.json, worklist.json, page_coverage.json, and source crops in
    output_folder. All are PRIVATE customer-derived artifacts.
    """
    if manifest.get("schema") != SCHEMA or manifest.get("source_sha256") != sha256(pdf_bytes):
        raise ValueError("Manifest schema/source PDF checksum mismatch")
    if not (1 <= scale <= 8):
        raise ValueError("scale must be within [1,8]")
    pages = manifest.get("pages")
    symbols = manifest.get("symbols")
    if not isinstance(pages, list) or not pages or not isinstance(symbols, list):
        raise ValueError("Manifest pages and symbols required")
    page_index: dict[int, dict] = {}
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for p in pages:
            n = p.get("page_1based")
            if not isinstance(n, int) or isinstance(n, bool) or n in page_index or not 1 <= n <= len(pdf):
                raise ValueError("Duplicate or invalid page inventory")
            if p.get("role") not in PAGE_ROLES or not isinstance(p.get("reviewed_complete"), bool):
                raise ValueError(f"Page {n} has invalid role/reviewed_complete status")
            expected = p.get("expected_symbol_items")
            if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool) or expected < 0):
                raise ValueError("expected_symbol_items must be nonnegative integer or null")
            dims = [round(pdf[n - 1].rect.width, 2), round(pdf[n - 1].rect.height, 2)]
            if p.get("page_dimensions_display_pdf_pt") != dims:
                raise ValueError(f"Page {n} dimensions differ; wrong PDF or coordinate space")
            page_index[n] = p
        approved: list[dict] = []
        worklist: list[dict] = []
        seen: set[str] = set()
        used_images: set[str] = set()
        out = Path(output_folder)
        out.mkdir(parents=True, exist_ok=True)
        crops = out / "source_crops"; crops.mkdir(exist_ok=True)
        for row in symbols:
            identity = row.get("id")
            n = row.get("page_1based")
            if not isinstance(identity, str) or not identity or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in identity):
                raise ValueError("Symbol ID must be a safe nonempty slug")
            if identity in seen:
                raise ValueError(f"Duplicate symbol ID: {identity}")
            seen.add(identity)
            if n not in page_index:
                raise ValueError(f"Symbol {identity} references unregistered page")
            page = pdf[n - 1]
            glyph_box = normalize_bbox(row.get("glyph_bbox_pdf_pt"), page, identity + "/glyph")
            label_box = normalize_bbox(row.get("label_bbox_pdf_pt"), page, identity + "/label")
            if _area_of_intersection(glyph_box, label_box) > 0:
                raise ValueError(f"{identity}: glyph overlaps label; crop is not clean")
            label = row.get("label_verbatim", "")
            status = row.get("review_status", "needs_review")
            if status not in CLASS_STATUSES:
                raise ValueError(f"{identity}: invalid review status")
            if status == "approved":
                # Review state must not be inferred from scores/boolean flags.
                a = row.get("glyph_reviewer", "")
                b = row.get("label_reviewer", "")
                if not (isinstance(label, str) and label.strip() and
                        isinstance(row.get("class_code"), str) and
                        row["class_code"].strip() and
                        isinstance(a, str) and a.strip() and isinstance(b, str) and
                        b.strip() and a.strip() != b.strip() and
                        row.get("glyph_isolated_confirmed") is True and
                        row.get("label_paired_confirmed") is True):
                    raise ValueError(f"{identity}: needs a nonempty class, distinct reviewers, and explicit glyph/label checks")
            picture = _crop(page, glyph_box, scale=scale)
            gr = picture.convert("L")
            px = list(gr.get_flattened_data())
            dark = sum(k < 160 for k in px)
            fraction = dark / len(px)
            if dark < 12 or fraction > 0.80:
                raise ValueError(f"{identity}: implausible glyph crop; dark pixels={dark}, fraction={fraction:.2f}")
            # Preserve original pixel colors so editorial markup cannot be silently 'cleaned'.
            template_name = f"{identity}_glyph.png"
            if template_name in used_images: raise ValueError("Duplicate output path")
            used_images.add(template_name)
            picture.save(crops / template_name)
            _crop(page, label_box, scale=scale).save(crops / f"{identity}_label.png")
            record = {
                "id": identity,
                "page_1based": n,
                "label_verbatim": label,
                "class_code": row.get("class_code"),
                "glyph_bbox_pdf_pt": glyph_box,
                "label_bbox_pdf_pt": label_box,
                "review_status": status,
                "glyph_image": f"source_crops/{template_name}",
                "label_image": f"source_crops/{identity}_label.png",
                "glyph_ink_fraction": round(fraction, 5),
                "source_sha256": sha256(pdf_bytes),
                "glyph_reviewer": row.get("glyph_reviewer"),
                "label_reviewer": row.get("label_reviewer"),
                "ports_review_status": row.get("ports_review_status", "UNVERIFIED"),
            }
            if status == "approved": approved.append(record)
            else: worklist.append(record)
        coverage = []
        for n, p in sorted(page_index.items()):
            mapped = sum(s.get("page_1based") == n and s.get("review_status") != "rejected" for s in symbols)
            app = sum(s["page_1based"] == n for s in approved)
            expected = p["expected_symbol_items"]
            # For sheets with no glyphs (e.g., line notes), engineer may set 0.
            complete = (p["reviewed_complete"] and expected is not None and mapped == expected and app == expected)
            coverage.append({"page_1based": n, "role": p["role"], "expected": expected,
                             "mapped_nonrejected": mapped, "approved": app,
                             "page_library_ready": bool(complete)})
    ready = bool(coverage) and all(p["page_library_ready"] for p in coverage)
    summary = {"schema": SCHEMA, "source_sha256": sha256(pdf_bytes),
               "library_readiness": "READY" if ready else "NOT_READY",
               "legend_pages_in_inventory": len(coverage),
               "pages_approved_complete": sum(p["page_library_ready"] for p in coverage),
               "glyphs_reviewed_and_approved": len(approved),
               "glyphs_pending_or_rejected": len(worklist),
               "independently_measured_detector_accuracy": None,
               "notice": "A library READY gate is NOT P&ID recognition or port-graph validation."}
    for name, data in (("approved.json", approved), ("worklist.json", worklist),
                       ("page_coverage.json", coverage), ("summary.json", summary)):
        (out / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return summary


def propose_glyph_rows(pdf_bytes: bytes, page_1based: int,
                       glyph_x: tuple[float, float], label_x: tuple[float, float],
                       y_bounds: tuple[float, float], *, scale: int = 3,
                       merge_gap_pt: float = 2.5,
                       id_prefix: str = "CAND") -> list[dict[str, Any]]:
    """Find ink-row proposals within a manually identified COLUMN, not classes.

    This image-projection heuristic merely reduces repeated drawing of crop
    rectangles. One glyph may be split; two glyphs may merge; editorial markup
    may look like a glyph.  All output requires independent visual review.
    Source PDF pages are 1-based and PDF-point boxes use displayed rotation.
    """
    if not (scale >= 1 and scale <= 8 and merge_gap_pt >= 0):
        raise ValueError("Invalid raster scale or merge gap")
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        if not 1 <= page_1based <= len(pdf): raise ValueError("Page out of range")
        pg=pdf[page_1based-1]
        x0,x1=glyph_x;lx0,lx1=label_x;y0,y1=y_bounds
        normalize_bbox([x0,y0,x1,y1],pg,"glyph column")
        normalize_bbox([lx0,y0,lx1,y1],pg,"label column")
        if max(x0,lx0)<min(x1,lx1): raise ValueError("Glyph and label columns overlap")
        img=_crop(pg,[x0,y0,x1,y1],scale=scale).convert("L")
        import numpy as np
        gray=np.asarray(img)
        counts=(gray<160).sum(axis=1)
        # Require some dark ink across each band; thin hairlines must survive.
        occupied=counts>=2
        runs=[];beg=None
        for i,v in enumerate(occupied):
            if v and beg is None:beg=i
            elif not v and beg is not None:runs.append([beg,i-1]);beg=None
        if beg is not None:runs.append([beg,len(occupied)-1])
        merged=[]
        for beg,end in runs:
            if merged and beg-merged[-1][1] <= round(merge_gap_pt*scale):
                merged[-1][1]=end
            else:merged.append([beg,end])
        result=[]
        for beg,end in merged:
            if end-beg < max(3,round(1.5*scale)):continue
            lo=max(y0,y0+beg/scale-1.0);hi=min(y1,y0+(end+1)/scale+1.0)
            n=len(result)+1
            result.append({
                "id":f"{id_prefix}_{n:03d}","page_1based":page_1based,
                "glyph_bbox_pdf_pt":[round(x0,2),round(lo,2),round(x1,2),round(hi,2)],
                "label_bbox_pdf_pt":[round(lx0,2),round(lo,2),round(lx1,2),round(hi,2)],
                "label_verbatim":"","class_code":None,"review_status":"needs_review",
                "glyph_isolated_confirmed":False,"label_paired_confirmed":False,
                "ports_review_status":"UNVERIFIED",
                "proposal_warning":"POSSIBLY_MERGED_ROWS" if hi-lo>23 else "PROPOSAL_ONLY",
            })
        return result
