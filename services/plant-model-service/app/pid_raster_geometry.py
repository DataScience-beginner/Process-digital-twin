"""Optional local raster geometry stage, conservatively labelled as unverified.

Built for scanned synthetic fixtures. Production symbol detection will require
trained domain-specific models and evaluation across industrial drawing styles.
"""
from __future__ import annotations

import hashlib
import io
import math

import fitz
from PIL import Image

RASTER_SCALE = 2.0
MAX_RASTER_SEGMENTS = 12000
MAX_RASTER_SHAPES = 5000


def _rect_close(a: list[float], b: list[float], tol: float = 3.0) -> bool:
    return max(abs(x - y) for x, y in zip(a, b)) <= tol


def extract_raster_evidence(pdf: bytes, pages_with_vector: set[int]) -> dict:
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"segments": [], "primitives": [],
                "warnings": ["Optional OpenCV unavailable: raster shapes/lines not extracted"]}
    primitives, segments, warnings = [], [], []
    with fitz.open(stream=pdf, filetype="pdf") as document:
        for page_idx, page in enumerate(document, 1):
            if page_idx in pages_with_vector:
                continue
            pix = page.get_pixmap(
                matrix=fitz.Matrix(RASTER_SCALE, RASTER_SCALE), alpha=False
            )
            if pix.width * pix.height > 15_000_000:
                warnings.append(f"Page {page_idx}: raster rendering exceeds pixel budget")
                continue
            source = np.asarray(
                Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
            )
            _, foreground = cv2.threshold(source, 180, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(
                foreground, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
            )
            for i, contour in enumerate(contours):
                if len(primitives) >= MAX_RASTER_SHAPES:
                    warnings.append("Raster shape limit reached")
                    break
                area = cv2.contourArea(contour) / (RASTER_SCALE ** 2)
                if not (80 < area < 100000):
                    continue
                perimeter = cv2.arcLength(contour, True)
                if perimeter <= 0:
                    continue
                polygon = cv2.approxPolyDP(contour, .025 * perimeter, True)
                x, y, width, height = cv2.boundingRect(contour)
                w, h = width / RASTER_SCALE, height / RASTER_SCALE
                if not (12 <= w <= 200 and 12 <= h <= 220):
                    continue
                kind = None
                if len(polygon) == 3 and .35 < w / h < 2.5:
                    kind = "triangle"
                elif len(polygon) == 4 and w >= 16 and h >= 16:
                    kind = "rectangle"
                elif 6 <= len(polygon) <= 15 and .75 < w / h < 1.3:
                    kind = "circle"
                if not kind:
                    continue
                bbox = [round(x / RASTER_SCALE, 2), round(y / RASTER_SCALE, 2),
                        round((x + width) / RASTER_SCALE, 2),
                        round((y + height) / RASTER_SCALE, 2)]
                if any(p["page"] == page_idx and p["type"] == kind
                       and _rect_close(p["bbox"], bbox) for p in primitives):
                    continue
                primitives.append({
                    "id": f"RASTER-P{page_idx}-C{i}", "page": page_idx,
                    "type": kind, "bbox": bbox,
                    "source": "opencv_contour_unverified",
                })
            found = cv2.HoughLinesP(
                foreground, 1, math.pi / 180,
                threshold=70, minLineLength=78, maxLineGap=5,
            )
            if found is None:
                continue
            for i, line in enumerate(found):
                if len(segments) >= MAX_RASTER_SEGMENTS:
                    warnings.append("Raster line limit reached")
                    break
                x1, y1, x2, y2 = [round(float(v) / RASTER_SCALE, 2)
                                  for v in line[0]]
                if abs(x1-x2) > 1.7 and abs(y1-y2) > 1.7:
                    continue
                segments.append({
                    "id": f"RASTER-P{page_idx}-H{i}",
                    "page": page_idx,
                    "start": [x1, y1], "end": [x2, y2],
                    "bbox": [min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)],
                    "length": round(math.hypot(x2-x1, y2-y1),2),
                    "source": "opencv_houghline_unverified",
                })
    return {"primitives": primitives, "segments": segments, "warnings": warnings}
