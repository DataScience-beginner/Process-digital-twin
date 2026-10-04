from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field

from .models import PlantModel
from .views import Point


class DraftPass(StrEnum):
    SHEET_INTENT = "sheet_intent"
    EQUIPMENT = "equipment"
    NOZZLES = "nozzles"
    PRIMARY_PIPING = "primary_piping"
    SECONDARY_PIPING = "secondary_piping"
    INLINE_COMPONENTS = "inline_components"
    CLEANUP = "cleanup"


class DraftObject(BaseModel):
    semantic_object_id: str
    position: Point
    visible: bool = True


class DraftRoute(BaseModel):
    semantic_edge_ids: list[str]
    role: str
    points: list[Point] = Field(min_length=2)


class DraftIssue(BaseModel):
    severity: str
    code: str
    message: str


class DrafterPlan(BaseModel):
    drawing_id: str
    passes_completed: list[DraftPass]
    objects: dict[str, DraftObject]
    routes: list[DraftRoute]
    issues: list[DraftIssue] = Field(default_factory=list)

    @property
    def status(self) -> str:
        if any(issue.severity == "RED" for issue in self.issues):
            return "RED"
        if self.issues:
            return "AMBER"
        return "GREEN"


PRIMARY_OBJECTS = {
    "EQ-V101",
    "VLV-LCV101",
    "VLV-XV101",
    "EQ-P101",
    "JUNC-P101-DIS",
    "VLV-NRV101",
    "VLV-XV102",
    "BOUND-PRODUCT",
    "VLV-FCV101",
}

NOZZLE_OBJECTS = {
    "NOZ-V101-LIQ",
    "NOZ-V101-REC",
    "NOZ-P101-SUC",
    "NOZ-P101-DIS",
}


def _p(x: float, y: float) -> Point:
    return Point(x=x, y=y)


def build_drafter_skeleton(model: PlantModel) -> DrafterPlan:
    # Pass 1: sheet intent. Main process story is separator -> pump -> process.
    # Pass 2: place major equipment with enough protected white space.
    objects = {
        "EQ-V101": DraftObject(semantic_object_id="EQ-V101", position=_p(220, 300)),
        "EQ-P101": DraftObject(semantic_object_id="EQ-P101", position=_p(690, 430)),
        # Pass 3: nozzle orientation follows service and equipment convention.
        "NOZ-V101-LIQ": DraftObject(semantic_object_id="NOZ-V101-LIQ", position=_p(220, 405), visible=False),
        "NOZ-V101-REC": DraftObject(semantic_object_id="NOZ-V101-REC", position=_p(256, 255), visible=False),
        "NOZ-P101-SUC": DraftObject(semantic_object_id="NOZ-P101-SUC", position=_p(664, 430), visible=False),
        "NOZ-P101-DIS": DraftObject(semantic_object_id="NOZ-P101-DIS", position=_p(716, 430), visible=False),
        # Pass 5: inline components sit on established piping corridors.
        "VLV-LCV101": DraftObject(semantic_object_id="VLV-LCV101", position=_p(395, 430)),
        "VLV-XV101": DraftObject(semantic_object_id="VLV-XV101", position=_p(535, 430)),
        "JUNC-P101-DIS": DraftObject(semantic_object_id="JUNC-P101-DIS", position=_p(785, 430)),
        "VLV-NRV101": DraftObject(semantic_object_id="VLV-NRV101", position=_p(865, 430)),
        "VLV-XV102": DraftObject(semantic_object_id="VLV-XV102", position=_p(955, 430)),
        "BOUND-PRODUCT": DraftObject(semantic_object_id="BOUND-PRODUCT", position=_p(1060, 430)),
        "VLV-FCV101": DraftObject(semantic_object_id="VLV-FCV101", position=_p(520, 255)),
    }

    required = set(objects)
    missing = sorted(required - {obj.id for obj in model.objects})
    if missing:
        raise ValueError(f"Drafter skeleton missing semantic objects: {', '.join(missing)}")

    # Pass 4: protect a continuous primary corridor before secondary routing.
    primary = DraftRoute(
        semantic_edge_ids=["C-LIQ-01", "C-LIQ-02", "C-SUC-02"],
        role="primary_suction",
        points=[
            _p(220, 405),
            _p(220, 430),
            _p(376, 430),
            _p(414, 430),
            _p(518, 430),
            _p(552, 430),
            _p(664, 430),
        ],
    )
    discharge = DraftRoute(
        semantic_edge_ids=["C-DIS-01", "C-DIS-02", "C-DIS-03", "C-DIS-04"],
        role="primary_discharge",
        points=[
            _p(716, 430),
            _p(785, 430),
            _p(848, 430),
            _p(882, 430),
            _p(938, 430),
            _p(972, 430),
            _p(1046, 430),
        ],
    )

    # Pass 5: minimum-flow recycle is routed around, not through, primary equipment.
    recycle = DraftRoute(
        semantic_edge_ids=["C-REC-01", "C-REC-02", "C-REC-03"],
        role="minimum_flow_recycle",
        points=[
            _p(785, 430),
            _p(785, 255),
            _p(539, 255),
            _p(501, 255),
            _p(300, 255),
            _p(256, 255),
        ],
    )

    plan = DrafterPlan(
        drawing_id="PID-DEMO-001-SKELETON",
        passes_completed=[
            DraftPass.SHEET_INTENT,
            DraftPass.EQUIPMENT,
            DraftPass.NOZZLES,
            DraftPass.PRIMARY_PIPING,
            DraftPass.SECONDARY_PIPING,
            DraftPass.INLINE_COMPONENTS,
        ],
        objects=objects,
        routes=[primary, discharge, recycle],
    )

    plan.issues.extend(check_skeleton_quality(plan))
    plan.passes_completed.append(DraftPass.CLEANUP)
    return plan


def check_skeleton_quality(plan: DrafterPlan) -> list[DraftIssue]:
    issues: list[DraftIssue] = []

    for route in plan.routes:
        for a, b in zip(route.points, route.points[1:]):
            if a.x != b.x and a.y != b.y:
                issues.append(
                    DraftIssue(
                        severity="RED",
                        code="NON_ORTHOGONAL_SEGMENT",
                        message=f"{route.role} contains a non-orthogonal segment.",
                    )
                )

    # Ensure the protected main corridor is a continuous process story.
    primary_roles = {route.role for route in plan.routes}
    for role in {"primary_suction", "primary_discharge", "minimum_flow_recycle"}:
        if role not in primary_roles:
            issues.append(
                DraftIssue(
                    severity="RED",
                    code="MISSING_CORRIDOR",
                    message=f"Required drafter corridor '{role}' is missing.",
                )
            )

    # Minimum clearance check for major equipment.
    vessel = plan.objects["EQ-V101"].position
    pump = plan.objects["EQ-P101"].position
    if pump.x - vessel.x < 350:
        issues.append(
            DraftIssue(
                severity="AMBER",
                code="EQUIPMENT_SPACING",
                message="Vessel-to-pump spacing is below the preferred drafting corridor.",
            )
        )

    return issues
