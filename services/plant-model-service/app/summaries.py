from __future__ import annotations

from typing import Any

from .models import Equipment, Instrument, Valve, ValveType
from .simulation import publish_demo_simulation
from .thread_models import ObjectDossier, RecordDomain


def _record_rows(dossiers: dict[str, ObjectDossier], domain: RecordDomain | None = None):
    seen = set()
    rows = []
    for dossier in dossiers.values():
        for record_domain, records in dossier.records.items():
            if domain is not None and record_domain != domain:
                continue
            for record in records:
                if record.id in seen:
                    continue
                seen.add(record.id)
                rows.append(record)
    return rows


def build_bdep_summaries(
    *,
    model,
    dossiers: dict[str, ObjectDossier],
    inspection: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    entities = inspection["entities"]

    equipment = []
    valves = []
    control_valves = []
    instruments = []
    psvs = []

    for obj in model.objects:
        row = {
            "object_id": obj.id,
            "tag": obj.tag,
            "type": (
                getattr(getattr(obj, "equipment_type", None), "value", None)
                or getattr(getattr(obj, "valve_type", None), "value", None)
                or getattr(getattr(obj, "instrument_type", None), "value", None)
                or getattr(getattr(obj, "junction_type", None), "value", None)
                or obj.category
            ),
            "service": obj.service,
        }
        if isinstance(obj, Equipment):
            equipment.append(row)
        elif isinstance(obj, Valve):
            parent = entities.get(obj.id, {}).get("parent_equipment")
            row["parent_equipment"] = parent.get("label") if parent else None
            valves.append(row)
            if obj.valve_type == ValveType.CONTROL:
                control_valves.append(row.copy())
            if obj.valve_type == ValveType.RELIEF:
                psvs.append(row.copy())
        elif isinstance(obj, Instrument):
            parent = entities.get(obj.id, {}).get("parent_equipment")
            row["parent_equipment"] = parent.get("label") if parent else None
            instruments.append(row)

    line_list = []
    for entity in entities.values():
        if entity.get("category") != "line":
            continue
        line_list.append(
            {
                "entity_id": entity["id"],
                "line_number": entity.get("line_number") or entity.get("tag"),
                "stream_number": entity.get("stream_number"),
                "type": entity.get("object_type"),
                "service": entity.get("service"),
                "from": (entity.get("from") or {}).get("label"),
                "to": (entity.get("to") or {}).get("label"),
                "through": " → ".join(
                    ref.get("label") or ref.get("id")
                    for ref in entity.get("through") or []
                ),
                "selected_nps_in": (
                    entity.get("record_value", {}).get("selected_nps_in")
                    if isinstance(entity.get("record_value"), dict)
                    else None
                ),
                "status": entity.get("status"),
            }
        )

    streams = []
    for case_id, label in [
        ("CASE-NORMAL", "Normal"),
        ("CASE-MAX", "Maximum"),
        ("CASE-TURNDOWN", "Turndown"),
    ]:
        publication = publish_demo_simulation(case_id)
        for stream in publication.streams:
            streams.append(
                {
                    "case": label,
                    "stream_number": stream.stream_number,
                    "simulator_stream_id": stream.simulator_stream_id,
                    "phase": stream.phase,
                    "mass_flow_tph": stream.mass_flow,
                    "temperature_degC": stream.temperature,
                    "pressure_barg": stream.pressure,
                    "density_kgm3": stream.density,
                    "source_equipment": stream.source_equipment_id,
                    "destination_equipment": stream.destination_equipment_id,
                }
            )

    calculations = []
    for record in _record_rows(dossiers):
        detail = (record.metadata or {}).get("calculation_detail")
        if not isinstance(detail, dict):
            continue
        trace = detail.get("trace") or {}
        calculations.append(
            {
                "calculation_id": record.id,
                "domain": record.domain.value,
                "name": record.name,
                "status": record.status,
                "governing_case": detail.get("governing_case")
                or detail.get("preliminary_selected_scenario"),
                "trace_id": trace.get("trace_id"),
                "qualification": trace.get("qualification"),
                "source": record.provenance.source_id,
                "revision": record.provenance.source_revision,
            }
        )

    control_loops = []
    for record in _record_rows(dossiers, RecordDomain.INSTRUMENTATION):
        if not isinstance(record.value, dict):
            continue
        if not {"controller", "final_element"} & set(record.value):
            continue
        control_loops.append(
            {
                "record_id": record.id,
                "name": record.name,
                "measurement": record.value.get("measurement"),
                "controller": record.value.get("controller"),
                "final_element": record.value.get("final_element"),
                "signal_standard": record.value.get("signal_standard"),
                "fail_position": record.value.get("valve_fail_position"),
                "status": record.status,
            }
        )

    relief_summary = []
    for record in _record_rows(dossiers, RecordDomain.PROCESS_CALC):
        if not record.id.startswith("RELIEF-"):
            continue
        value = record.value if isinstance(record.value, dict) else {}
        relief_summary.append(
            {
                "record_id": record.id,
                "psv": "PSV-101",
                "protected_equipment": "V-101",
                "governing_scenario": value.get("governing_scenario"),
                "relief_load_tph": value.get("relief_load_tph"),
                "set_pressure_barg": value.get("set_pressure_barg"),
                "required_area_in2": value.get("required_orifice_area_in2"),
                "selected_orifice": value.get("selected_orifice"),
                "selected_area_in2": value.get("selected_orifice_area_in2"),
                "selected_capacity_tph": value.get("selected_capacity_tph"),
                "status": record.status,
            }
        )

    technical = []
    for record in _record_rows(dossiers, RecordDomain.MECHANICAL):
        technical.append(
            {
                "record_id": record.id,
                "name": record.name,
                "value": record.value,
                "status": record.status,
                "source": record.provenance.source_id,
            }
        )

    cost = []
    total = None
    for record in _record_rows(dossiers, RecordDomain.COST):
        row = {
            "record_id": record.id,
            "name": record.name,
            "value": record.value,
            "unit": record.unit,
            "status": record.status,
        }
        cost.append(row)
        if record.id == "COST-PACKAGE-TOTAL":
            total = row

    publication = []
    # Publication stages are displayed elsewhere; this register represents
    # discipline record maturity at summary level.
    for domain in RecordDomain:
        domain_records = _record_rows(dossiers, domain)
        publication.append(
            {
                "domain": domain.value,
                "record_count": len(domain_records),
                "published_or_checked": sum(
                    1
                    for record in domain_records
                    if "published" in record.status
                    or "checked" in record.status
                    or "selected" in record.status
                    or record.status == "calculated"
                ),
                "placeholder_or_gated": sum(
                    1
                    for record in domain_records
                    if "placeholder" in record.status
                    or "gated" in record.status
                    or "tbd" in str(record.value).lower()
                ),
            }
        )

    return {
        "equipment_list": equipment,
        "stream_list": streams,
        "line_list": line_list,
        "valve_list": valves,
        "control_valve_list": control_valves,
        "instrument_index": instruments,
        "control_loop_list": control_loops,
        "psv_relief_summary": relief_summary,
        "calculation_register": calculations,
        "technical_summary": technical,
        "cost_summary": cost,
        "publication_summary": publication,
        "project_total": [total] if total else [],
    }
