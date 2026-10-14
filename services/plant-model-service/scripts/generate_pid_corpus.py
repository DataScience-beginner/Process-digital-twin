"""Generate original, reproducible P&ID test inputs without third-party drawings.

Usage: python scripts/generate_pid_corpus.py [output_directory]
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import fitz
from PIL import Image


def _text(page, x, y, value, size=11):
    page.insert_text((x, y), value, fontsize=size, fontname="helv")


def _page(page, variant="baseline"):
    sh = page.new_shape()
    pen = (0, 0, 0)

    # Vessel / pump and deliberately separated process line segments.
    sh.draw_rect(fitz.Rect(70, 140, 164, 283))
    sh.draw_circle(fitz.Point(545, 210), 30)
    sh.draw_line((164, 210), (305, 210))
    sh.draw_line((355, 210), (515, 210))
    sh.draw_line((575, 210), (705, 210))

    # Deliberately drawn control valve: two opposing triangles.
    sh.draw_polyline([(305, 191), (330, 210), (305, 229), (305, 191)])
    sh.draw_polyline([(355, 191), (330, 210), (355, 229), (355, 191)])
    sh.draw_line((330, 210), (330, 175))
    sh.draw_circle(fitz.Point(330, 166), 9)

    # Pressure safety valve connected to upper nozzle.
    sh.draw_line((114, 140), (114, 108))
    sh.draw_polyline([(100, 105), (128, 105), (114, 85), (100, 105)])
    sh.draw_line((114, 85), (114, 57))

    # Instrument sensing point and distinct signal connection.
    sh.draw_line((114, 283), (114, 306))
    sh.draw_circle(fitz.Point(114, 330), 18)
    sh.finish(color=pen, fill=None, width=1.6)
    sh.commit()
    _text(page, 89, 168, "V-101")
    _text(page, 526, 259, "P-101")
    _text(page, 296, 153, "FCV-101")
    _text(page, 135, 97, "PSV-101")
    _text(page, 93, 334, "PT-101", size=8)
    _text(page, 640, 192, "LINE-1102", size=8)
    _text(page, 40, 40, "SYNTHETIC P&ID - BDEP TEST ONLY", size=12)
    _text(page, 40, 391, f"PID-SYN-{variant.upper()} | NOT FOR ENGINEERING USE", size=9)

    if variant in ("complex", "multisheet"):
        # Crossing without a junction. Useful negative test.
        sh = page.new_shape()
        sh.draw_line((437, 170), (437, 251))
        sh.draw_line((403, 170), (473, 170))
        sh.draw_line((403, 251), (473, 251))
        sh.finish(color=(0, 0, 0), width=0.8, dashes="[3 3] 0")
        sh.commit()
        _text(page, 390, 160, "SIGNAL", size=8)
        _text(page, 630, 285, "CONT. SHEET-02", size=9)


def _build_vector(out: Path, variant="baseline", pages=1) -> Path:
    document = fitz.open()
    for n in range(pages):
        page = document.new_page(width=760, height=420)
        _page(page, variant=variant)
        if pages > 1:
            page.insert_text((480, 40), f"SHEET {n+1} OF {pages}", fontsize=12)
    filename = f"{variant}.pdf"
    document.save(out / filename, garbage=4, deflate=True)
    document.close()
    return out / filename


def _build_elbow_crossing(out: Path) -> Path:
    """Multi-stroke elbows, plus non-connected solid interior crossing."""
    doc = fitz.open()
    page = doc.new_page(width=760, height=420)
    sh = page.new_shape()
    sh.draw_rect(fitz.Rect(70, 120, 150, 245))
    sh.draw_circle(fitz.Point(560, 210), 30)
    # V-101 to FCV-101 via two distinct elbow joins.
    sh.draw_line((150, 180), (200, 180))
    sh.draw_line((200, 180), (200, 280))
    sh.draw_line((200, 280), (305, 280))
    sh.draw_polyline([(305, 261), (330, 280), (305, 299), (305, 261)])
    sh.draw_polyline([(355, 261), (330, 280), (355, 299), (355, 261)])
    # FCV-101 to P-101 via two more elbows.
    sh.draw_line((355, 280), (440, 280))
    sh.draw_line((440, 280), (440, 210))
    sh.draw_line((440, 210), (530, 210))
    # Solid crossing at two line interiors: MUST NOT become a junction.
    sh.draw_line((250, 245), (250, 315))
    # Dashed signal crosses process line, not a process junction.
    sh.finish(color=(0, 0, 0), width=1.6)
    sh.commit()
    sh = page.new_shape()
    sh.draw_line((160, 230), (260, 230))
    sh.finish(color=(0, 0, 0), width=.8, dashes="[3 3] 0")
    sh.commit()
    for x, y, tag in [
        (82, 151, "V-101"), (525, 260, "P-101"),
        (292, 244, "FCV-101"), (38, 35, "BDEP SYNTHETIC ELBOW TOPOLOGY"),
    ]:
        _text(page, x, y, tag, 10)
    target = out / "elbow_crossing.pdf"
    doc.save(target, garbage=4, deflate=True)
    doc.close()
    return target


def generate(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = _build_vector(output_dir)
    _build_vector(output_dir, "complex")
    _build_vector(output_dir, "multisheet", pages=2)
    _build_elbow_crossing(output_dir)

    original = fitz.open(base)
    original_page = original[0]
    image = original_page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False).tobytes("png")
    (output_dir / "raster.png").write_bytes(image)
    photo = Image.open(io.BytesIO(image)).convert("RGB")
    photo.save(output_dir / "compressed.jpg", quality=58)

    scanned = fitz.open()
    page = scanned.new_page(width=760, height=420)
    page.insert_image(page.rect, stream=image)
    scanned.save(output_dir / "scanned.pdf", garbage=4, deflate=True)
    scanned.close()
    original.close()

    expected = {
        "source": "generated; not plant engineering",
        "fixture": "baseline.pdf",
        "expected_tags": ["V-101", "P-101", "FCV-101", "PSV-101", "PT-101"],
        "known_process_adjacencies": [
            ["V-101", "FCV-101"],
            ["FCV-101", "P-101"]
        ],
        "negative_example": "Crossing of instrument signal and process piping is not a process junction.",
        "extra_fixture": "elbow_crossing.pdf",
        "expected_elbow_adjacencies": [["V-101", "FCV-101"], ["FCV-101", "P-101"]],
        "note": "Graph labels are benchmark ground truth; extraction must not copy them during inference."
    }
    (output_dir / "expected_graph.json").write_text(json.dumps(expected, indent=2))
    return {"output": str(output_dir), "files": sorted(p.name for p in output_dir.iterdir())}


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/pid_corpus/generated")
    print(json.dumps(generate(root), indent=2))
