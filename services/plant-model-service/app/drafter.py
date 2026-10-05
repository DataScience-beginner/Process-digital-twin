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
    PROTECTION = "protection"
    INSTRUMENTATION = "instrumentation"
    SIGNALS = "signals"
    ANNOTATION = "annotation"
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



def build_drafter_instrumented(model: PlantModel) -> DrafterPlan:
    """Build MVP 0.5B on top of the frozen 0.5A process skeleton."""
    plan = build_drafter_skeleton(model)

    additions = {
        # Protection / utility items
        "VLV-PSV101": DraftObject(semantic_object_id="VLV-PSV101", position=_p(235, 145)),
        "BOUND-RELIEF": DraftObject(semantic_object_id="BOUND-RELIEF", position=_p(235, 72)),
        "VLV-VENT101": DraftObject(semantic_object_id="VLV-VENT101", position=_p(145, 150)),
        "BOUND-VENT": DraftObject(semantic_object_id="BOUND-VENT", position=_p(82, 150)),
        "VLV-DRAIN101": DraftObject(semantic_object_id="VLV-DRAIN101", position=_p(195, 520)),
        "BOUND-DRAIN": DraftObject(semantic_object_id="BOUND-DRAIN", position=_p(195, 570)),
        # Vessel instruments
        "INS-PT101": DraftObject(semantic_object_id="INS-PT101", position=_p(105, 255)),
        "INS-PI101": DraftObject(semantic_object_id="INS-PI101", position=_p(105, 310)),
        "INS-LT101": DraftObject(semantic_object_id="INS-LT101", position=_p(315, 290)),
        "INS-LI101": DraftObject(semantic_object_id="INS-LI101", position=_p(315, 340)),
        "INS-LIC101": DraftObject(semantic_object_id="INS-LIC101", position=_p(415, 205)),
        # Pump / recycle instruments
        "INS-PI101S": DraftObject(semantic_object_id="INS-PI101S", position=_p(610, 360)),
        "INS-PI101D": DraftObject(semantic_object_id="INS-PI101D", position=_p(730, 360)),
        "INS-FT101": DraftObject(semantic_object_id="INS-FT101", position=_p(700, 215)),
        "INS-FIC101": DraftObject(semantic_object_id="INS-FIC101", position=_p(820, 180)),
    }

    missing = sorted(set(additions) - {obj.id for obj in model.objects})
    if missing:
        raise ValueError(f"Instrumented drafter plan missing semantic objects: {', '.join(missing)}")
    plan.objects.update(additions)

    # Protection / vent / drain routes. Each begins on the actual vessel shell.
    plan.routes.extend([
        DraftRoute(
            semantic_edge_ids=["C-PSV-01", "C-PSV-02"],
            role="psv_relief",
            points=[_p(235, 222), _p(235, 166), _p(235, 124), _p(235, 80)],
        ),
        DraftRoute(
            semantic_edge_ids=["C-VENT-01", "C-VENT-02"],
            role="vessel_vent",
            points=[_p(195, 226), _p(195, 150), _p(162, 150), _p(128, 150), _p(96, 150)],
        ),
        DraftRoute(
            semantic_edge_ids=["C-DRAIN-01", "C-DRAIN-02"],
            role="vessel_drain",
            points=[_p(195, 374), _p(195, 503), _p(195, 537), _p(195, 562)],
        ),
        # Thin process/instrument take-offs.
        DraftRoute(
            semantic_edge_ids=["A-PT101"],
            role="pressure_to_pt",
            points=[_p(184, 255), _p(120, 255)],
        ),
        DraftRoute(
            semantic_edge_ids=["A-PI101"],
            role="pressure_to_pi",
            points=[_p(184, 255), _p(150, 255), _p(150, 310), _p(120, 310)],
        ),
        DraftRoute(
            semantic_edge_ids=["A-LT101"],
            role="level_to_lt",
            points=[_p(256, 290), _p(300, 290)],
        ),
        DraftRoute(
            semantic_edge_ids=["A-LI101"],
            role="level_to_li",
            points=[_p(256, 290), _p(280, 290), _p(280, 340), _p(300, 340)],
        ),
        DraftRoute(
            semantic_edge_ids=["A-PI-SUC"],
            role="pump_suction_pi",
            points=[_p(610, 430), _p(610, 374)],
        ),
        DraftRoute(
            semantic_edge_ids=["A-PI-DIS"],
            role="pump_discharge_pi",
            points=[_p(730, 430), _p(730, 374)],
        ),
        # Control signals are routed only after all process piping is frozen.
        DraftRoute(
            semantic_edge_ids=["S-LEVEL-01"],
            role="level_signal",
            points=[_p(330, 290), _p(365, 290), _p(365, 205), _p(400, 205)],
        ),
        DraftRoute(
            semantic_edge_ids=["S-LEVEL-02"],
            role="level_control_signal",
            points=[_p(415, 220), _p(415, 365), _p(395, 365), _p(395, 390)],
        ),
        DraftRoute(
            semantic_edge_ids=["S-FLOW-01"],
            role="flow_signal",
            points=[_p(700, 201), _p(700, 180), _p(805, 180)],
        ),
        DraftRoute(
            semantic_edge_ids=["S-FLOW-02"],
            role="flow_control_signal",
            points=[_p(820, 195), _p(820, 205), _p(520, 205), _p(520, 215)],
        ),
    ])

    # Insert explicit drafting passes before the final cleanup marker.
    if plan.passes_completed and plan.passes_completed[-1] == DraftPass.CLEANUP:
        plan.passes_completed.pop()
    plan.passes_completed.extend([
        DraftPass.PROTECTION,
        DraftPass.INSTRUMENTATION,
        DraftPass.SIGNALS,
        DraftPass.ANNOTATION,
        DraftPass.CLEANUP,
    ])

    plan.drawing_id = "PID-DEMO-001-INSTRUMENTED"
    plan.issues = check_skeleton_quality(plan)
    return plan
