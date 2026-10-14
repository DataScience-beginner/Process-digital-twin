"""Source-aligned training annotations exported only after explicit symbol review.

The JSON structure is COCO-inspired; image coordinates refer to the same PNG
resolution served by /pages/{page}.png. Geometry and tag reviews are separate.
"""
from __future__ import annotations

from typing import Any


def build_verified_annotation_export(import_id: str, import_data: dict[str, Any]) -> dict:
    candidates = {
        c["id"]: c for c in import_data.get("candidates", [])
        if c["review_status"] == "accepted"
    }
    valid = [
        s for s in import_data.get("symbol_hypotheses", [])
        if s.get("review_status") == "accepted"
        and s["tag_id"] in candidates
        and s.get("geometry_id") is not None
        and s.get("symbol_type_from_tag") is not None
    ]
    types = sorted({s["symbol_type_from_tag"] for s in valid})
    class_id = {name: i + 1 for i, name in enumerate(types)}
    pages = {
        int(p["page"]): p for p in import_data.get("pages", [])
    }
    images = []
    for page_num, metadata in sorted(pages.items()):
        width, height = metadata["width"], metadata["height"]
        scale = min(1.6, 1800 / max(width, height))
        images.append({
            "id": page_num,
            "file_name": f"pages/{page_num}.png",
            "width": round(width * scale),
            "height": round(height * scale),
            "source_pdf_page": page_num,
            "render_scale": scale,
        })
    by_page = {i["id"]: i for i in images}
    annotations = []
    for number, symbol in enumerate(valid, start=1):
        p = by_page[symbol["page"]]
        factor = p["render_scale"]
        x0, y0, x1, y1 = symbol["bbox"]
        if x1 <= x0 or y1 <= y0:
            continue
        annotations.append({
            "id": number,
            "image_id": symbol["page"],
            "category_id": class_id[symbol["symbol_type_from_tag"]],
            "bbox": [
                round(x0 * factor, 2), round(y0 * factor, 2),
                round((x1 - x0) * factor, 2), round((y1 - y0) * factor, 2),
            ],
            "area": round((x1 - x0) * (y1 - y0) * factor * factor, 2),
            "iscrowd": 0,
            "source_tag": symbol["tag"],
            "candidate_id": symbol["tag_id"],
            "source_geometry_ids": symbol.get("geometry_ids", []),
            "reviewed_by": symbol.get("reviewed_by"),
            "source_bbox_pdf_points": symbol["bbox"],
        })
    return {
        "info": {
            "description": "BDEP verified source-linked symbol annotations",
            "import_id": import_id,
            "document_sha256": import_data["document_sha256"],
            "coordinate_space": "PNG pixel coordinates matching BDEP page preview",
            "provenance": "engineer-reviewed tag AND separately reviewed symbol",
            "train_test_split_note": "Split by entire source P&ID/document; never by drawing patch",
            "unreviewed_and_rejected_excluded": True,
        },
        "images": images,
        "annotations": annotations,
        "categories": [
            {"id": class_id[name], "name": name} for name in types
        ],
    }
