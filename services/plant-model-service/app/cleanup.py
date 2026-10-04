from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field

from .drafter import DrafterPlan, DraftIssue
from .views import Point


class AnnotationKind(StrEnum):
    LINE_TAG = "line_tag"
    EQUIPMENT_TAG = "equipment_tag"
    OFFPAGE = "offpage"
    NOTE = "note"
    TITLE = "title"


class AnnotationPlacement(BaseModel):
    annotation_id: str
    text: str
    kind: AnnotationKind
    position: Point
    width: float
    height: float
    related_ids: list[str] = Field(default_factory=list)


class ProtectedZone(BaseModel):
    zone_id: str
    x: float
    y: float
    width: float
    height: float


class CleanupResult(BaseModel):
    annotations: list[AnnotationPlacement]
    protected_zones: list[ProtectedZone]
    issues: list[DraftIssue] = Field(default_factory=list)

    @property
    def status(self) -> str:
        if any(issue.severity == "RED" for issue in self.issues):
            return "RED"
        if self.issues:
            return "AMBER"
        return "GREEN"


def _overlap(a: AnnotationPlacement, b: AnnotationPlacement) -> bool:
    return not (
        a.position.x + a.width <= b.position.x
        or b.position.x + b.width <= a.position.x
        or a.position.y + a.height <= b.position.y
        or b.position.y + b.height <= a.position.y
    )


def _inside_zone(a: AnnotationPlacement, z: ProtectedZone) -> bool:
    return not (
        a.position.x + a.width <= z.x
        or z.x + z.width <= a.position.x
        or a.position.y + a.height <= z.y
        or z.y + z.height <= a.position.y
    )


def build_cleanup(plan: DrafterPlan) -> CleanupResult:
    annotations = [
        AnnotationPlacement(
            annotation_id="ANN-L-V101-LIQ",
            text="L-V101-LIQ",
            kind=AnnotationKind.LINE_TAG,
            position=Point(x=270, y=410),
            width=60, height=12,
            related_ids=["C-LIQ-01"],
        ),
        AnnotationPlacement(
            annotation_id="ANN-L-P101-DIS",
            text="L-P101-DIS",
            kind=AnnotationKind.LINE_TAG,
            position=Point(x=745, y=410),
            width=64, height=12,
            related_ids=["C-DIS-01"],
        ),
        AnnotationPlacement(
            annotation_id="ANN-L-P101-REC",
            text="L-P101-REC",
            kind=AnnotationKind.LINE_TAG,
            position=Point(x=585, y=235),
            width=64, height=12,
            related_ids=["C-REC-01"],
        ),
        AnnotationPlacement(
            annotation_id="ANN-OP-PROCESS",
            text="TO PROCESS / CONT.",
            kind=AnnotationKind.OFFPAGE,
            position=Point(x=1000, y=452),
            width=86, height=12,
            related_ids=["BOUND-PRODUCT"],
        ),
        AnnotationPlacement(
            annotation_id="ANN-OP-RELIEF",
            text="TO RELIEF HEADER",
            kind=AnnotationKind.OFFPAGE,
            position=Point(x=258, y=72),
            width=88, height=12,
            related_ids=["BOUND-RELIEF"],
        ),
        AnnotationPlacement(
            annotation_id="ANN-OP-VENT",
            text="TO VENT",
            kind=AnnotationKind.OFFPAGE,
            position=Point(x=55, y=166),
            width=42, height=12,
            related_ids=["BOUND-VENT"],
        ),
        AnnotationPlacement(
            annotation_id="ANN-OP-DRAIN",
            text="TO CLOSED DRAIN",
            kind=AnnotationKind.OFFPAGE,
            position=Point(x=213, y=561),
            width=78, height=12,
            related_ids=["BOUND-DRAIN"],
        ),
        AnnotationPlacement(
            annotation_id="ANN-NOTE-1",
            text="1. PROCESS SKELETON IS PROTECTED BEFORE INSTRUMENT AND ANNOTATION PLACEMENT.",
            kind=AnnotationKind.NOTE,
            position=Point(x=45, y=607),
            width=485, height=11,
        ),
        AnnotationPlacement(
            annotation_id="ANN-NOTE-2",
            text="2. DIGITAL THREAD METADATA REMAINS AVAILABLE IN GRAPH VIEW.",
            kind=AnnotationKind.NOTE,
            position=Point(x=45, y=621),
            width=390, height=11,
        ),
    ]

    protected_zones = [
        ProtectedZone(zone_id="TITLE_BLOCK", x=760, y=592, width=325, height=62),
        ProtectedZone(zone_id="DRAWING_BORDER_TOP", x=24, y=24, width=1072, height=18),
    ]

    issues = check_cleanup_quality(
        annotations=annotations,
        protected_zones=protected_zones,
        sheet_width=1120,
        sheet_height=690,
    )
    return CleanupResult(
        annotations=annotations,
        protected_zones=protected_zones,
        issues=issues,
    )


def check_cleanup_quality(
    *,
    annotations: list[AnnotationPlacement],
    protected_zones: list[ProtectedZone],
    sheet_width: float,
    sheet_height: float,
) -> list[DraftIssue]:
    issues: list[DraftIssue] = []

    for ann in annotations:
        if (
            ann.position.x < 24
            or ann.position.y < 24
            or ann.position.x + ann.width > sheet_width - 24
            or ann.position.y + ann.height > sheet_height - 24
        ):
            issues.append(
                DraftIssue(
                    severity="RED",
                    code="ANNOTATION_OUT_OF_BOUNDS",
                    message=f"{ann.annotation_id} is outside the drawing border.",
                )
            )

    for i, first in enumerate(annotations):
        for second in annotations[i + 1:]:
            if _overlap(first, second):
                issues.append(
                    DraftIssue(
                        severity="AMBER",
                        code="ANNOTATION_OVERLAP",
                        message=f"{first.annotation_id} overlaps {second.annotation_id}.",
                    )
                )

    for ann in annotations:
        if ann.kind in {AnnotationKind.LINE_TAG, AnnotationKind.OFFPAGE}:
            for zone in protected_zones:
                if zone.zone_id == "TITLE_BLOCK" and _inside_zone(ann, zone):
                    issues.append(
                        DraftIssue(
                            severity="AMBER",
                            code="PROTECTED_ZONE_INTRUSION",
                            message=f"{ann.annotation_id} intrudes into {zone.zone_id}.",
                        )
                    )

    return issues
