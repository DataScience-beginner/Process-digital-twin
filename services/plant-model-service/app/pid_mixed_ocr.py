"""OCR for *mixed-content* engineering PDF pages.

Typical exported CAD P&IDs have selectable title block text but rasterized
instrument bubbles and tag strings. The M1 OCR stage skipped such pages.
This module examines the drawing area when native tag extraction is sparse,
and captures horizontal or vertically stacked instrument IDs with source
bounding boxes. All interpretations remain unreviewed candidates.
"""
from __future__ import annotations

import hashlib
import io
import re
from collections import defaultdict

import fitz
from PIL import Image

from .pid_digitization import TAG_PATTERN, _kind

MAX_OCR_PIXELS = 10_000_000
ALLOWED_LETTER_CODES = re.compile(r"^[A-Z]{1,5}$")
LOOP_NUMBER = re.compile(r"^\d{3,7}[A-Z]?$")
PROJECT_INSTRUMENT_PREFIX = {
    "FAL", "FAH", "FE", "FIT", "FQ", "FI", "FR", "FY", "FIC",
    "LAH", "LAL", "LAHH", "LIT", "LIC", "LSH", "LSL", "LSHH",
    "PIT", "PDIT", "PDT", "PAH", "PAL", "PI", "PT", "PIC",
    "TIT", "TIC", "TAH", "TAL", "TI", "TT",
    "HS", "HC", "ES", "ZSC", "ZSO", "ZIC",
}
LIMIT = 500


def _has_code(token: str) -> bool:
    return (
        bool(ALLOWED_LETTER_CODES.fullmatch(token))
        and token in PROJECT_INSTRUMENT_PREFIX
    )


def _mid(box):
    return ((box[0]+box[2])/2, (box[1]+box[3])/2)


def _candidate(sha: str, page_number: int, words: list[dict],
               method: str) -> dict | None:
    label = words[0]["word"]
    digit = words[1]["word"] if len(words) > 1 else ""
    if len(words) == 1:
        match = TAG_PATTERN.fullmatch(label)
        if match is None:
            return None
        prefix, loop = match.groups()
    else:
        if not _has_code(label) or not LOOP_NUMBER.fullmatch(digit):
            return None
        prefix, loop = label, digit
    tag = f"{prefix.upper()}-{loop.upper()}"
    xs = [v for w in words for v in (w["bbox"][0],w["bbox"][2])]
    ys = [v for w in words for v in (w["bbox"][1],w["bbox"][3])]
    bbox = [round(min(xs),2),round(min(ys),2),
            round(max(xs),2),round(max(ys),2)]
    category, typ = _kind(prefix.upper())
    if category == "unmapped" and prefix.upper() in PROJECT_INSTRUMENT_PREFIX:
        # This is an instrumentation label but not a typed PlantModel enum;
        # leave it UNMAPPED until approved client symbol/dictionary mapping.
        category = "unmapped"
    score = round(min(w["ocr_confidence"] for w in words),2)
    identifier = hashlib.sha256(
        f"{sha}:{page_number}:{tag}:{bbox}:{method}".encode()
    ).hexdigest()[:16]
    return {
        "id": identifier, "tag": tag, "category": category, "object_type": typ,
        "page": page_number, "bbox": bbox,
        "source_text": " / ".join(w["word"] for w in words),
        "review_status": "unreviewed",
        "confidence": "ocr_candidate_unvalidated",
        "ocr_confidence": score,
        "source_method": method,
        "inferred_vertical_stack": method.endswith("vertical_stack"),
        "client_legend_mapping_status": "unverified",
    }


def extract_mixed_page_ocr(pdf_bytes: bytes, *,
                           native_tag_count_by_page: dict[int, int],
                           threshold: int = 8) -> tuple[list[dict], list[str], list[dict]]:
    warnings = []
    stats = []
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        return [], ["Local pytesseract OCR extra is not installed"], []
    candidates = []
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_index, page in enumerate(doc):
            page_number = page_index + 1
            existing = native_tag_count_by_page.get(page_number,0)
            if existing >= threshold:
                stats.append({"page":page_number,"status":"not_required",
                              "native_tag_candidates":existing})
                continue
            # Exclude right-side drawing title block to prevent false tags
            # arising from project numbers, drawing numbers and addresses.
            clip = fitz.Rect(0, 0, page.rect.width*.89, page.rect.height*.94)
            factor = min(2.0, (MAX_OCR_PIXELS/(clip.width*clip.height))**.5)
            factor = max(1.0, factor)
            try:
                pix=page.get_pixmap(matrix=fitz.Matrix(factor,factor),
                                   clip=clip,alpha=False)
                raster=Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                res=pytesseract.image_to_data(
                    raster,output_type=Output.DICT,config="--psm 11"
                )
            except Exception as exc:
                warnings.append(
                    f"Page {page_number}: mixed-content OCR failed: {type(exc).__name__}"
                )
                stats.append({"page":page_number,"status":"unavailable"})
                continue
            tokens=[]
            for i,raw in enumerate(res["text"]):
                word=str(raw).upper().strip(".,()[]{}\"':; ")
                if not word:
                    continue
                try:
                    conf=float(res["conf"][i])
                except (TypeError,ValueError):
                    conf=-1
                if conf<35:
                    continue
                x=float(res["left"][i])
                y=float(res["top"][i])
                w=float(res["width"][i])
                h=float(res["height"][i])
                tokens.append({
                    "word":word, "ocr_confidence":conf,
                    "bbox":[round(clip.x0+x/factor,2),
                            round(clip.y0+y/factor,2),
                            round(clip.x0+(x+w)/factor,2),
                            round(clip.y0+(y+h)/factor,2)],
                    "line":(res["block_num"][i],res["par_num"][i],
                            res["line_num"][i]),
                })
            matched=set()
            proposals=[]
            for idx,word in enumerate(tokens):
                candidate=_candidate(
                    sha,page_number,[word],"local_tesseract_mixed_direct"
                )
                if candidate:
                    proposals.append(candidate)
                if not _has_code(word["word"]):
                    continue
                wx,wy=_mid(word["bbox"])
                for j,number in enumerate(tokens):
                    if j==idx or not LOOP_NUMBER.fullmatch(number["word"]):
                        continue
                    nx,ny=_mid(number["bbox"])
                    h=word["bbox"][3]-word["bbox"][1]
                    if word["line"]==number["line"] and 0<(
                        number["bbox"][0]-word["bbox"][2]
                    )<max(16, h*1.6):
                        mode="local_tesseract_mixed_same_line"
                    elif (abs(wx-nx)<=max(9,h*1.5)
                          and 0 < number["bbox"][1]-word["bbox"][3] <
                          max(22,h*2.3)):
                        mode="local_tesseract_mixed_vertical_stack"
                    else:
                        continue
                    pair=_candidate(sha,page_number,[word,number],mode)
                    if pair:
                        proposals.append(pair)
            for item in proposals:
                # Drop candidate duplicates (different OCR grouping for same
                # tag at very similar x/y); keep source evidence in each ID.
                key=(item["tag"],round(item["bbox"][0]/6),
                     round(item["bbox"][1]/6))
                if key in matched:
                    continue
                matched.add(key)
                candidates.append(item)
                if len(candidates)>=LIMIT:
                    warnings.append("Mixed-content OCR reached conservative 500-candidate limit")
                    break
            stats.append({
                "page":page_number, "status":"attempted",
                "drawing_area":"0-89% width, 0-94% height",
                "native_tag_candidates":existing,
                "ocr_tokens":len(tokens),
                "ocr_tag_candidates":len(matched),
                "stacked_loop_candidates":sum(c["inferred_vertical_stack"]
                                               for c in proposals),
                "bounding_box_coordinate_space":"source PDF points, top-left",
            })
            if len(candidates)>=LIMIT:
                break
    return candidates,warnings,stats
