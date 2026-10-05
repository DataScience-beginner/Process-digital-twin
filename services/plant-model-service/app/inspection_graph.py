from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import Nozzle, PlantModel
from .thread_models import ObjectDossier


ROUTE_ENTITY_IDS = {
    "primary_suction": "LINE-1102",
    "primary_discharge": "LINE-1103",
    "minimum_flow_recycle": "LINE-1190",
    "psv_relief": "LINE-PSV101",
    "vessel_vent": "LINE-VENT101",
    "vessel_drain": "LINE-DRAIN101",
    "pressure_to_pt": "CONN-PT101",
    "pressure_to_pi": "CONN-PI101",
    "level_to_lt": "CONN-LT101",
    "level_to_li": "CONN-LI101",
    "pump_suction_pi": "CONN-PI101S",
    "pump_discharge_pi": "CONN-PI101D",
    "level_signal": "SIGNAL-LT101-LIC101",
    "level_control_signal": "SIGNAL-LIC101-LCV101",
    "flow_signal": "SIGNAL-FT101-FIC101",
    "flow_control_signal": "SIGNAL-FIC101-FCV101",
}

LINE_SPECS = {
    "LINE-1102": {
        "role": "primary_suction",
        "record_id": "LINE-1102-SIZING",
        "tag": "1102",
        "service": "V-101 liquid outlet / P-101 suction",
        "entity_type": "process_line",
    },
    "LINE-1103": {
        "role": "primary_discharge",
        "record_id": "LINE-1103-SIZING",
        "tag": "1103",
        "service": "P-101 discharge to downstream process",
        "entity_type": "process_line",
    },
    "LINE-1190": {
        "role": "minimum_flow_recycle",
        "record_id": "LINE-1190-SIZING",
        "tag": "1190",
        "service": "P-101 minimum-flow recycle to V-101",
        "entity_type": "process_line",
    },
    "LINE-PSV101": {
        "role": "psv_relief",
        "tag": "PSV-101 RELIEF",
        "service": "V-101 relief path to relief header",
        "entity_type": "relief_line",
    },
    "LINE-VENT101": {
        "role": "vessel_vent",
        "tag": "V-101 VENT",
        "service": "V-101 vent path",
        "entity_type": "vent_line",
    },
    "LINE-DRAIN101": {
        "role": "vessel_drain",
        "tag": "V-101 DRAIN",
        "service": "V-101 closed-drain path",
        "entity_type": "drain_line",
    },
    "CONN-PT101": {
        "role": "pressure_to_pt",
        "tag": "PT-101 TAKE-OFF",
        "service": "Pressure measurement take-off",
        "entity_type": "instrument_connection",
    },
    "CONN-PI101": {
        "role": "pressure_to_pi",
        "tag": "PI-101 TAKE-OFF",
        "service": "Local pressure indication take-off",
        "entity_type": "instrument_connection",
    },
    "CONN-LT101": {
        "role": "level_to_lt",
        "tag": "LT-101 CONNECTION",
        "service": "Level transmitter connection",
        "entity_type": "instrument_connection",
    },
    "CONN-LI101": {
        "role": "level_to_li",
        "tag": "LI-101 CONNECTION",
        "service": "Level indicator connection",
        "entity_type": "instrument_connection",
    },
    "CONN-PI101S": {
        "role": "pump_suction_pi",
        "tag": "PI-101S TAKE-OFF",
        "service": "Pump suction pressure indication take-off",
        "entity_type": "instrument_connection",
    },
    "CONN-PI101D": {
        "role": "pump_discharge_pi",
        "tag": "PI-101D TAKE-OFF",
        "service": "Pump discharge pressure indication take-off",
        "entity_type": "instrument_connection",
    },
    "SIGNAL-LT101-LIC101": {
        "role": "level_signal",
        "tag": "LT-101 → LIC-101",
        "service": "Level measurement signal",
        "entity_type": "signal_connection",
    },
    "SIGNAL-LIC101-LCV101": {
        "role": "level_control_signal",
        "tag": "LIC-101 → LCV-101",
        "service": "Level controller output",
        "entity_type": "signal_connection",
    },
    "SIGNAL-FT101-FIC101": {
        "role": "flow_signal",
        "tag": "FT-101 → FIC-101",
        "service": "Minimum-flow measurement signal",
        "entity_type": "signal_connection",
    },
    "SIGNAL-FIC101-FCV101": {
        "role": "flow_control_signal",
        "tag": "FIC-101 → FCV-101",
        "service": "Minimum-flow controller output",
        "entity_type": "signal_connection",
    },
}


def route_entity_id(role: str) -> str:
    return ROUTE_ENTITY_IDS.get(role, f"ROUTE-{role.upper()}")


def _object_type(obj) -> str:
    for attr in (
        "equipment_type",
        "valve_type",
        "instrument_type",
        "junction_type",
        "nozzle_type",
    ):
        value = getattr(obj, attr, None)
        if value is not None:
            return getattr(value, "value", str(value))
    return obj.category


def _label(model: PlantModel, object_id: str) -> str:
    try:
        return model.object(object_id).tag
    except KeyError:
        return object_id


def _ref(model: PlantModel, object_id: str, relation: str | None = None) -> dict[str, Any]:
    try:
        obj = model.object(object_id)
        return {
            "id": obj.id,
            "label": obj.tag,
            "category": obj.category,
            "object_type": _object_type(obj),
            "service": obj.service,
            "relation": relation,
        }
    except KeyError:
        return {
            "id": object_id,
            "label": object_id,
            "category": "unknown",
            "object_type": None,
            "service": None,
            "relation": relation,
        }


def _module_owners(model: PlantModel) -> tuple[dict[str, str], dict[str, list[str]]]:
    owner_by_child: dict[str, str] = {}
    children_by_owner: dict[str, list[str]] = defaultdict(list)

    for module in model.modules:
        equipment_ids = [
            member_id
            for member_id in module.member_ids
            if getattr(model.object(member_id), "category", None) == "equipment"
        ]
        if len(equipment_ids) != 1:
            continue
        owner_id = equipment_ids[0]
        for member_id in module.member_ids:
            if member_id == owner_id:
                continue
            owner_by_child.setdefault(member_id, owner_id)
            children_by_owner[owner_id].append(member_id)

    for obj in model.objects:
        if isinstance(obj, Nozzle):
            owner_by_child[obj.id] = obj.parent_equipment_id
            if obj.id not in children_by_owner[obj.parent_equipment_id]:
                children_by_owner[obj.parent_equipment_id].append(obj.id)

    return owner_by_child, children_by_owner


def _edge_endpoints(model: PlantModel, edge_id: str) -> tuple[str, str, str] | None:
    for conn in model.connections:
        if conn.id == edge_id:
            return conn.source.object_id, conn.target.object_id, conn.kind.value
    for assoc in model.associations:
        if assoc.id == edge_id:
            return assoc.subject_id, assoc.target_id, assoc.relationship
    return None


def _ordered_path(model: PlantModel, edge_ids: list[str]) -> list[str]:
    raw: list[str] = []
    for edge_id in edge_ids:
        endpoints = _edge_endpoints(model, edge_id)
        if endpoints is None:
            continue
        source_id, target_id, _ = endpoints
        if not raw:
            raw.extend([source_id, target_id])
            continue
        if raw[-1] == source_id:
            raw.append(target_id)
        elif raw[-1] == target_id:
            raw.append(source_id)
        else:
            if source_id not in raw:
                raw.append(source_id)
            if target_id not in raw:
                raw.append(target_id)

    # Include the owning equipment at process/instrument nozzle boundaries so the
    # user sees the engineering story, not just hidden nozzle nodes.
    expanded: list[str] = []
    for index, object_id in enumerate(raw):
        obj = model.object(object_id)
        if isinstance(obj, Nozzle) and index == 0:
            expanded.append(obj.parent_equipment_id)
        if object_id not in expanded:
            expanded.append(object_id)
        if isinstance(obj, Nozzle) and index == len(raw) - 1:
            if obj.parent_equipment_id not in expanded:
                expanded.append(obj.parent_equipment_id)
    return expanded


def _line_record_lookup(dossiers: dict[str, ObjectDossier]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for dossier in dossiers.values():
        for records in dossier.records.values():
            for record in records:
                if record.id.startswith("LINE-") and record.id not in found:
                    found[record.id] = record
    return found


def build_inspection_graph(
    model: PlantModel,
    dossiers: dict[str, ObjectDossier],
    routes: list,
) -> dict[str, Any]:
    owner_by_child, children_by_owner = _module_owners(model)
    entities: dict[str, dict[str, Any]] = {}
    relation_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for obj in model.objects:
        owner_id = owner_by_child.get(obj.id)
        entities[obj.id] = {
            "id": obj.id,
            "tag": obj.tag,
            "category": obj.category,
            "object_type": _object_type(obj),
            "service": obj.service,
            "properties": obj.properties,
            "parent_equipment": _ref(model, owner_id, "belongs_to") if owner_id else None,
            "children": [],
            "relationships": [],
            "connected_lines": [],
            "dossier_id": obj.id if obj.id in dossiers else None,
        }

    for owner_id, child_ids in children_by_owner.items():
        if owner_id in entities:
            entities[owner_id]["children"] = [
                _ref(model, child_id, "contains")
                for child_id in sorted(set(child_ids), key=lambda item: _label(model, item))
            ]

    for conn in model.connections:
        relation_rows[conn.source.object_id].append(
            _ref(model, conn.target.object_id, f"outgoing_{conn.kind.value}")
        )
        relation_rows[conn.target.object_id].append(
            _ref(model, conn.source.object_id, f"incoming_{conn.kind.value}")
        )

    inverse = {
        "protects": "protected_by",
        "has_nozzle": "nozzle_of",
        "measures_pressure_at": "measured_by",
        "indicates_pressure_at": "indicated_by",
        "measures_level_at": "measured_by",
        "indicates_level_at": "indicated_by",
    }
    for assoc in model.associations:
        relation_rows[assoc.subject_id].append(
            _ref(model, assoc.target_id, assoc.relationship)
        )
        relation_rows[assoc.target_id].append(
            _ref(model, assoc.subject_id, inverse.get(assoc.relationship, f"inverse_{assoc.relationship}"))
        )

        # If an instrument is associated to a nozzle, also surface the owning
        # equipment as a relationship without changing the semantic graph.
        target = model.object(assoc.target_id)
        if isinstance(target, Nozzle):
            relation_rows[assoc.subject_id].append(
                _ref(model, target.parent_equipment_id, "related_equipment")
            )
            relation_rows[target.parent_equipment_id].append(
                _ref(model, assoc.subject_id, assoc.relationship)
            )

    for object_id, rows in relation_rows.items():
        if object_id not in entities:
            continue
        dedup: dict[tuple[str, str | None], dict[str, Any]] = {}
        for row in rows:
            dedup[(row["id"], row.get("relation"))] = row
        entities[object_id]["relationships"] = list(dedup.values())

    line_records = _line_record_lookup(dossiers)
    route_by_role = {route.role: route for route in routes}

    for entity_id, spec in LINE_SPECS.items():
        route = route_by_role.get(spec["role"])
        if route is None:
            continue

        path_ids = _ordered_path(model, route.semantic_edge_ids)
        path_refs = [_ref(model, object_id, "path") for object_id in path_ids]
        record = line_records.get(spec.get("record_id")) if spec.get("record_id") else None
        line_number = None
        stream_number = None
        value = None
        metadata = None
        provenance = None
        status = "semantic"
        if record is not None:
            value = record.value
            metadata = record.metadata
            provenance = record.provenance.model_dump(mode="json")
            status = record.status
            if isinstance(record.value, dict):
                line_number = record.value.get("line_number")
                stream_number = record.value.get("stream_number")

        tag = line_number or spec["tag"]
        line_entity = {
            "id": entity_id,
            "tag": tag,
            "category": "line" if spec["entity_type"].endswith("line") else "connection",
            "object_type": spec["entity_type"],
            "service": spec["service"],
            "route_role": spec["role"],
            "record_id": spec.get("record_id"),
            "semantic_edge_ids": route.semantic_edge_ids,
            "path": path_refs,
            "from": path_refs[0] if path_refs else None,
            "to": path_refs[-1] if path_refs else None,
            "through": path_refs[1:-1] if len(path_refs) > 2 else [],
            "line_number": line_number,
            "stream_number": stream_number,
            "engineering_record_id": record.id if record is not None else None,
            "record_value": value,
            "record_metadata": metadata,
            "record_provenance": provenance,
            "status": status,
        }
        entities[entity_id] = line_entity

        for index, object_id in enumerate(path_ids):
            if object_id not in entities or entities[object_id].get("category") in {"line", "connection"}:
                continue
            direction = "through"
            if index == 0:
                direction = "out"
            elif index == len(path_ids) - 1:
                direction = "in"
            entities[object_id]["connected_lines"].append(
                {
                    "id": entity_id,
                    "label": tag,
                    "service": spec["service"],
                    "direction": direction,
                    "object_type": spec["entity_type"],
                }
            )

    return {
        "entities": entities,
        "route_entity_ids": {
            role: route_entity_id(role)
            for role in route_by_role
        },
    }
