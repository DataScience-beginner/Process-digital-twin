from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring


def _type_name(obj) -> str:
    for attr in ("equipment_type", "valve_type", "instrument_type", "junction_type", "nozzle_type"):
        value = getattr(obj, attr, None)
        if value is not None:
            return getattr(value, "value", str(value))
    return obj.category


def export_dexpi_oriented_xml(model, inspection: dict[str, Any]) -> bytes:
    """Create a DEXPI-XML-oriented semantic export.

    The root follows the DEXPI XML Model concept and the mapping is explicit,
    but this prototype is intentionally marked as not schema-validated. The
    production exporter must validate against the official DEXPI 2.0.1 schema
    and company profile before issue.
    """
    root = Element(
        "Model",
        {
            "name": model.project_id,
            "uri": f"urn:digital-bdep:{model.project_id}",
            "exportProfile": "DEXPI-2.0.1-oriented-demo",
            "schemaValidation": "PENDING",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    imports = SubElement(root, "Imports")
    for name in ("Builtin", "Core", "Plant", "Process"):
        SubElement(imports, "Import", {"name": name})

    objects = SubElement(root, "Objects")
    for obj in model.objects:
        item = SubElement(
            objects,
            "Object",
            {
                "id": obj.id,
                "type": _type_name(obj),
                "category": obj.category,
            },
        )
        SubElement(item, "DataProperty", {"name": "TagName"}).text = obj.tag
        if obj.service:
            SubElement(item, "DataProperty", {"name": "Service"}).text = obj.service
        parent = inspection["entities"].get(obj.id, {}).get("parent_equipment")
        if parent:
            SubElement(
                item,
                "Association",
                {"name": "ParentEquipment", "target": f'#{parent["id"]}'},
            )

    connections = SubElement(root, "Connections")
    for conn in model.connections:
        SubElement(
            connections,
            "Connection",
            {
                "id": conn.id,
                "kind": conn.kind.value,
                "source": f"#{conn.source.object_id}",
                "sourcePort": conn.source.port,
                "target": f"#{conn.target.object_id}",
                "targetPort": conn.target.port,
                "logicalLine": conn.logical_line or "",
            },
        )

    associations = SubElement(root, "Associations")
    for assoc in model.associations:
        SubElement(
            associations,
            "Association",
            {
                "id": assoc.id,
                "relationship": assoc.relationship,
                "subject": f"#{assoc.subject_id}",
                "target": f"#{assoc.target_id}",
                "targetPort": assoc.target_port or "",
            },
        )

    extensions = SubElement(root, "DigitalBDEPExtensions")
    for entity in inspection["entities"].values():
        if entity.get("category") != "line":
            continue
        line = SubElement(
            extensions,
            "EngineeringLine",
            {
                "id": entity["id"],
                "lineNumber": str(entity.get("line_number") or entity.get("tag") or ""),
                "streamNumber": str(entity.get("stream_number") or ""),
                "service": str(entity.get("service") or ""),
            },
        )
        for ref in entity.get("path") or []:
            SubElement(line, "PathObject", {"ref": f'#{ref["id"]}'})

    return tostring(root, encoding="utf-8", xml_declaration=True)


def export_summary_csv(summaries: dict[str, list[dict[str, Any]]], key: str) -> bytes:
    rows = summaries.get(key)
    if rows is None:
        raise KeyError(key)
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                field: (str(value) if isinstance(value, (dict, list, tuple)) else value)
                for field, value in row.items()
            }
        )
    return stream.getvalue().encode("utf-8-sig")


def export_visio_vdx_demo(model, plan) -> bytes:
    """Minimal Visio 2003 XML exchange prototype.

    This proves semantic object/route mapping. Production use should move to
    the company's approved VSDX/Visio stencil adapter.
    """
    ns = "urn:schemas-microsoft-com:office:visio"
    root = Element("VisioDocument", {"xmlns": ns})
    pages = SubElement(root, "Pages")
    page = SubElement(pages, "Page", {"ID": "1", "NameU": plan.drawing_id, "Name": plan.drawing_id})
    shapes = SubElement(page, "Shapes")

    sid = 1
    for object_id, draft in plan.objects.items():
        obj = model.object(object_id)
        shape = SubElement(
            shapes,
            "Shape",
            {"ID": str(sid), "NameU": obj.tag, "Name": obj.tag, "Type": "Shape"},
        )
        xform = SubElement(shape, "XForm")
        SubElement(xform, "PinX").text = str(round(draft.position.x / 100.0, 4))
        SubElement(xform, "PinY").text = str(round((690.0 - draft.position.y) / 100.0, 4))
        SubElement(xform, "Width").text = "0.45"
        SubElement(xform, "Height").text = "0.30"
        SubElement(shape, "Text").text = obj.tag
        props = SubElement(shape, "Prop")
        SubElement(props, "Label").text = "SemanticObjectID"
        SubElement(props, "Value").text = obj.id
        sid += 1

    for route in plan.routes:
        route_shape = SubElement(
            shapes,
            "Shape",
            {"ID": str(sid), "NameU": route.role, "Name": route.role, "Type": "Shape"},
        )
        SubElement(route_shape, "Text").text = ",".join(route.semantic_edge_ids)
        sid += 1

    return tostring(root, encoding="utf-8", xml_declaration=True)


def export_dxf_demo(model, plan) -> bytes:
    """ASCII DXF R12-style geometry prototype for CAD interchange."""
    rows = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]

    def add_line(x1, y1, x2, y2, layer):
        rows.extend([
            "0", "LINE", "8", layer,
            "10", f"{x1:.3f}", "20", f"{-y1:.3f}", "30", "0.0",
            "11", f"{x2:.3f}", "21", f"{-y2:.3f}", "31", "0.0",
        ])

    def add_text(x, y, text, layer):
        rows.extend([
            "0", "TEXT", "8", layer,
            "10", f"{x:.3f}", "20", f"{-y:.3f}", "30", "0.0",
            "40", "8.0", "1", text,
        ])

    for route in plan.routes:
        layer = "SIGNAL" if "signal" in route.role else "PROCESS"
        for a, b in zip(route.points, route.points[1:]):
            add_line(a.x, a.y, b.x, b.y, layer)

    for object_id, draft in plan.objects.items():
        obj = model.object(object_id)
        add_text(draft.position.x, draft.position.y, obj.tag, obj.category.upper())

    rows.extend(["0", "ENDSEC", "0", "EOF"])
    return ("\r\n".join(rows) + "\r\n").encode("ascii", errors="replace")


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def simple_text_pdf(title: str, lines: list[str]) -> bytes:
    """Small dependency-free PDF writer for auditable calculation exports."""
    page_width, page_height = 595, 842
    margin = 42
    line_height = 12
    usable = int((page_height - 2 * margin - 24) / line_height)
    pages = [lines[i:i + usable] for i in range(0, len(lines), usable)] or [[]]

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_entries = []

    for page_lines in pages:
        ops = ["BT", "/F1 9 Tf", f"{margin} {page_height - margin} Td"]
        ops.append(f"({_pdf_escape(title)}) Tj")
        ops.append("0 -18 Td")
        for line in page_lines:
            text = str(line)
            chunks = [text[i:i + 105] for i in range(0, len(text), 105)] or [""]
            for chunk in chunks:
                ops.append(f"({_pdf_escape(chunk)}) Tj")
                ops.append(f"0 -{line_height} Td")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1", errors="replace")
        content_id = add(
            f"<< /Length {len(stream)} >>\nstream\n".encode()
            + stream
            + b"\nendstream"
        )
        page_entries.append((content_id,))

    pages_id_placeholder = len(objects) + len(page_entries) + 1
    page_ids = []
    for (content_id,) in page_entries:
        page_id = add(
            (
                f"<< /Type /Page /Parent {pages_id_placeholder} 0 R "
                f"/MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode()
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_id = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
    if pages_id != pages_id_placeholder:
        raise RuntimeError("PDF object layout mismatch")
    catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def workspace_pdf_lines(entity: dict[str, Any], dossier) -> list[str]:
    lines = [
        f"Entity: {entity.get('tag') or entity['id']}",
        f"Entity ID: {entity['id']}",
        f"Type: {entity.get('object_type') or entity.get('category')}",
        f"Service: {entity.get('service') or ''}",
        "Design Basis: DB-001 Rev A",
        "",
    ]
    if dossier is not None:
        lines.append("DESIGN BASIS")
        for criterion in dossier.design_basis:
            lines.append(
                f"{criterion.id} | {criterion.name} = {criterion.value} {criterion.unit or ''} | "
                f"{criterion.provenance.source_id} Rev {criterion.provenance.source_revision or '-'}"
            )
        for domain, records in dossier.records.items():
            lines.extend(["", domain.value.upper()])
            for record in records:
                lines.append(f"{record.id} | {record.name} | Status={record.status}")
                lines.append(f"Output: {record.value} {record.unit or ''}")
                detail = (record.metadata or {}).get("calculation_detail")
                if not isinstance(detail, dict):
                    continue
                lines.append(f"Governing: {detail.get('governing_case') or detail.get('preliminary_selected_scenario')}")
                lines.append(f"Reason: {detail.get('governing_reason') or detail.get('selection_reason')}")
                trace = detail.get("trace") or {}
                for step in trace.get("steps") or []:
                    lines.append(
                        f"Step {step.get('step')}: {step.get('title')} | {step.get('equation')} | "
                        f"{step.get('substitution')} => {step.get('result')} {step.get('unit') or ''}"
                    )
                for check in trace.get("validation_checks") or []:
                    lines.append(
                        f"CHECK {check.get('result')}: {check.get('check')} | Actual={check.get('actual')} | "
                        f"Criterion={check.get('criterion')}"
                    )
    if entity.get("record_value"):
        lines.extend(["", "LINE / CONNECTION ENGINEERING", str(entity.get("record_value"))])
    return lines
