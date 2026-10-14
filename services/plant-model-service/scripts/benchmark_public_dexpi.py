"""Download/inspect official DEXPI reference P&ID as an external benchmark.

This is an independent, authentic standard sample, not a synthetic fixture.
Its XML is SEMANTIC REFERENCE DATA, not evidence that an image extraction
is correct. We report extraction *coverage* but cannot claim precision or
recall without drawing-level annotation alignment.

Source (DEXPI Specification 2.0.0, CC BY 4.0):
  https://dexpi.org/specification/2.0/html/appendix/reference_pid.html
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

REFERENCE_URL = "https://dexpi.org/specification/2.0/html/appendix/reference_pid.html"
XML_URL = "https://dexpi.org/specification/2.0/html/_static/reference_pid.xml"
SVG_URL = "https://dexpi.org/specification/2.0/html/_images/reference_pid.svg"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
MAX_BYTES = 16 * 1024 * 1024
TAG_LIMIT = 200
CLASS_LIMIT = 100


def get_public_file(url: str, *, limit: int = MAX_BYTES) -> bytes:
    """Bounded download of one fixed official source URL (never user supplied)."""
    if url not in (XML_URL, SVG_URL):
        raise ValueError("Only pinned official reference assets are permitted")
    request = Request(url, headers={"User-Agent": "Digital-BDEP-PID-Research/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Reference file exceeds input limit")
    return payload


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def summarize_dexpi_xml(content: bytes) -> dict:
    """Defensive structural summary only; not a full DEXPI 2.x importer."""
    if len(content) > MAX_BYTES:
        raise ValueError("XML too large")
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", content, re.I):
        raise ValueError("DTD/entities are not supported in reference import")
    root = ET.fromstring(content)
    if local_name(root.tag) != "Model":
        raise ValueError("Expected DEXPI Model root")
    kind_counts = Counter()
    type_counts = Counter()
    identifiers = []
    duplicate = set()
    visited = set()
    for element in root.iter():
        kind_counts[local_name(element.tag)] += 1
        obj_type = element.get("type")
        if obj_type:
            type_counts[obj_type] += 1
        obj_id = element.get("id")
        if obj_id:
            if obj_id in visited:
                duplicate.add(obj_id)
            visited.add(obj_id)
            if len(identifiers) < TAG_LIMIT:
                identifiers.append({
                    "id": obj_id,
                    "xml_element": local_name(element.tag),
                    "type": obj_type,
                })
    return {
        "root": local_name(root.tag),
        "root_name": root.get("name"),
        "object_count": kind_counts.get("Object", 0),
        "element_counts": dict(kind_counts.most_common(CLASS_LIMIT)),
        "type_counts": dict(type_counts.most_common(CLASS_LIMIT)),
        "sample_elements": identifiers,
        "duplicate_ids": sorted(duplicate)[:20],
        "schema_validation": "not_performed",
        "image_alignment": "not_performed",
        "standard_semantic_reference_only": True,
    }


def run_reference_benchmark(out: Path, *, fetch: bool = True) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    xml_path, svg_path = out / "reference_pid.xml", out / "reference_pid.svg"
    if fetch:
        xml = get_public_file(XML_URL)
        svg = get_public_file(SVG_URL)
        xml_path.write_bytes(xml)
        svg_path.write_bytes(svg)
    else:
        xml, svg = xml_path.read_bytes(), svg_path.read_bytes()
    if b"<svg" not in svg[:1000] and b":svg" not in svg[:1000]:
        raise ValueError("Reference graphic is not SVG")
    semantic = summarize_dexpi_xml(xml)
    report = {
        "source": REFERENCE_URL,
        "license": "CC BY 4.0",
        "license_url": LICENSE_URL,
        "attribution": "DEXPI Initiative, DEXPI Specification 2.0 Reference P&ID",
        "alterations": "none to downloaded XML and SVG",
        "source_format": "DEXPI XML paired with SVG engineering diagram",
        "xml_sha256": hashlib.sha256(xml).hexdigest(),
        "svg_sha256": hashlib.sha256(svg).hexdigest(),
        "xml_size_bytes": len(xml),
        "svg_size_bytes": len(svg),
        "semantic": semantic,
        "visual_extraction": {
            "status": "not_attempted",
            "note": "DEXPI XML is ground truth but comparison requires ID/geometry matching to SVG.",
        },
    }
    # Rasterize the actual DEXPI reference and attempt the SAME Brownfield
    # extraction pipeline as for scanned drawings, when optional tools exist.
    try:
        import cairosvg
        from app.pid_pipeline import build_pid_extraction
        from app.pid_digitization import MAX_PDF_BYTES
        png = cairosvg.svg2png(bytestring=svg, output_width=1500, unsafe=False)
        (out / "reference_pid.png").write_bytes(png)
        if len(png) > MAX_PDF_BYTES:
            raise ValueError("Reference PNG exceeds P&ID input limit")
        _, scan = build_pid_extraction(
            png, "reference_pid.png", ocr=True,
        )
        report["visual_extraction"] = {
            "status": "attempted",
            "text_tag_mentions": len(scan["candidates"]),
            "visual_shape_matches": sum(
                bool(s.get("geometry_id"))
                for s in scan["symbol_hypotheses"]
            ),
            "unreviewed_route_proposals": len(scan["connection_proposals"]),
            "warnings": scan["warnings"][:30],
            "precision_recall": "not_computed_without_aligned_ground_truth",
            "engineer_review": "required",
            "readme": "Counts describe method coverage, not extraction correctness.",
        }
    except (ImportError, ValueError, RuntimeError, OSError) as exc:
        report["visual_extraction"] = {
            "status": "not_completed",
            "reason": f"{type(exc).__name__}: {str(exc)[:300]}",
        }
    (out / "dexpi_reference_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True)
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path("data/pid_corpus/external/dexpi_2_0"))
    parser.add_argument("--existing", action="store_true",
                        help="Read already-downloaded files without network")
    args = parser.parse_args()
    print(json.dumps(run_reference_benchmark(args.out, fetch=not args.existing),
                     indent=2))


if __name__ == "__main__":
    main()
