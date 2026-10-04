from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CriterionCategory(StrEnum):
    FEED = "feed"
    BATTERY_LIMIT = "battery_limit"
    OPERATING_CASE = "operating_case"
    FLOW_MARGIN = "flow_margin"
    VESSEL = "vessel"
    PUMP = "pump"
    CONTROL_VALVE = "control_valve"
    RELIEF = "relief"
    LINE_SIZING = "line_sizing"
    MATERIALS = "materials"
    UTILITIES = "utilities"
    AMBIENT = "ambient"
    STANDARD = "standard"


class CriterionStatus(StrEnum):
    WORKING = "working"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class RecordDomain(StrEnum):
    DESIGN_BASIS = "design_basis"
    SIMULATION = "simulation"
    PROCESS_CALC = "process_calculation"
    PID = "pid"
    INSTRUMENTATION = "instrumentation"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    COST = "cost"
    EPC_VENDOR = "epc_vendor"
    OPERATIONS = "operations"
    HISTORY = "history"


class Provenance(BaseModel):
    source_type: str
    source_id: str
    source_revision: str | None = None
    method: str | None = None
    note: str | None = None


class DesignBasisCriterion(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: CriterionCategory
    value: Any
    unit: str | None = None
    revision: str = "A"
    status: CriterionStatus = CriterionStatus.APPROVED
    applies_to_categories: list[str] = Field(default_factory=list)
    applies_to_types: list[str] = Field(default_factory=list)
    target_object_ids: list[str] = Field(default_factory=list)
    provenance: Provenance

    def applies_to(self, *, object_id: str, category: str, object_type: str | None) -> bool:
        if self.target_object_ids and object_id in self.target_object_ids:
            return True
        if self.target_object_ids:
            return False
        if self.applies_to_categories and category not in self.applies_to_categories:
            return False
        if self.applies_to_types and (object_type is None or object_type not in self.applies_to_types):
            return False
        return bool(self.applies_to_categories or self.applies_to_types)


class DesignCase(BaseModel):
    id: str
    name: str
    case_type: str
    design_basis_revision: str
    status: str = "approved"


class EngineeringRecord(BaseModel):
    id: str
    object_id: str
    domain: RecordDomain
    name: str
    value: Any | None = None
    unit: str | None = None
    status: str = "working"
    provenance: Provenance
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObjectDossier(BaseModel):
    object_id: str
    tag: str
    category: str
    object_type: str | None = None
    service: str | None = None
    design_basis: list[DesignBasisCriterion] = Field(default_factory=list)
    records: dict[RecordDomain, list[EngineeringRecord]] = Field(default_factory=dict)

    def records_for(self, domain: RecordDomain) -> list[EngineeringRecord]:
        return self.records.get(domain, [])
