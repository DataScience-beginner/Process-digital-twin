from __future__ import annotations

from pydantic import BaseModel, Field

from .drafting import master_for
from .models import PlantModel


class Point(BaseModel):
    x: float
    y: float


class Representation(BaseModel):
    representation_id: str
    semantic_object_id: str
    symbol_master: str
    position: Point
    rotation: float = 0.0


class RouteRepresentation(BaseModel):
    route_id: str
    semantic_edge_id: str
    line_style: str
    points: list[Point] = Field(min_length=2)


class DrawingView(BaseModel):
    drawing_id: str
    drawing_type: str = "P&ID"
    representations: list[Representation]
    routes: list[RouteRepresentation] = Field(default_factory=list)

    def representation_for(self, semantic_object_id: str) -> Representation:
        for rep in self.representations:
            if rep.semantic_object_id == semantic_object_id:
                return rep
        raise KeyError(semantic_object_id)

    def validate_against(self, model: PlantModel) -> None:
        object_ids = {obj.id for obj in model.objects}
        edge_ids = {c.id for c in model.connections} | {a.id for a in model.associations}

        missing_objects = {
            rep.semantic_object_id
            for rep in self.representations
            if rep.semantic_object_id not in object_ids
        }
        if missing_objects:
            raise ValueError(
                f"Drawing {self.drawing_id} references unknown semantic objects: "
                f"{', '.join(sorted(missing_objects))}"
            )

        missing_edges = {
            route.semantic_edge_id
            for route in self.routes
            if route.semantic_edge_id not in edge_ids
        }
        if missing_edges:
            raise ValueError(
                f"Drawing {self.drawing_id} references unknown semantic edges: "
                f"{', '.join(sorted(missing_edges))}"
            )


POSITIONS: dict[str, tuple[float, float]] = {
    "EQ-V101": (210, 300),
    "NOZ-V101-FEED": (174, 286),
    "NOZ-V101-VAP": (210, 215),
    "NOZ-V101-LIQ": (220, 385),
    "NOZ-V101-REC": (246, 260),
    "NOZ-V101-VENT": (190, 215),
    "NOZ-V101-DRAIN": (195, 385),
    "NOZ-V101-PSV": (232, 215),
    "NOZ-V101-PT": (174, 250),
    "NOZ-V101-LT": (246, 305),
    "INS-PT101": (105, 245),
    "INS-PI101": (105, 300),
    "INS-LT101": (310, 285),
    "INS-LI101": (310, 335),
    "INS-LIC101": (420, 220),
    "VLV-LCV101": (420, 430),
    "VLV-PSV101": (235, 155),
    "BOUND-RELIEF": (235, 95),
    "VLV-VENT101": (145, 160),
    "BOUND-VENT": (78, 160),
    "VLV-DRAIN101": (195, 525),
    "BOUND-DRAIN": (195, 585),
    "EQ-P101": (655, 430),
    "NOZ-P101-SUC": (626, 430),
    "NOZ-P101-DIS": (684, 430),
    "NOZ-P101-DRAIN": (655, 456),
    "VLV-XV101": (535, 430),
    "JUNC-P101-DIS": (755, 430),
    "VLV-NRV101": (850, 430),
    "VLV-XV102": (940, 430),
    "BOUND-PRODUCT": (1055, 430),
    "INS-FT101": (755, 275),
    "INS-FIC101": (875, 205),
    "VLV-FCV101": (555, 275),
    "INS-PI101S": (610, 355),
    "INS-PI101D": (700, 355),
}


def _anchor(model: PlantModel, view: DrawingView, object_id: str, port_name: str) -> Point:
    obj = model.object(object_id)
    rep = view.representation_for(object_id)
    master = master_for(obj)
    ax, ay = master.anchors.get(port_name, (0.5, 0.5))
    return Point(
        x=rep.position.x - master.width / 2 + ax * master.width,
        y=rep.position.y - master.height / 2 + ay * master.height,
    )


def _orthogonal(source: Point, target: Point) -> list[Point]:
    if abs(source.y - target.y) < 1:
        return [source, target]
    if abs(source.x - target.x) < 1:
        return [source, target]
    mid_x = (source.x + target.x) / 2
    return [
        source,
        Point(x=mid_x, y=source.y),
        Point(x=mid_x, y=target.y),
        target,
    ]


def build_demo_pid_view(model: PlantModel) -> DrawingView:
    reps = []
    for obj in model.objects:
        if obj.id not in POSITIONS:
            continue
        x, y = POSITIONS[obj.id]
        reps.append(
            Representation(
                representation_id=f"REP-PID001-{obj.id}",
                semantic_object_id=obj.id,
                symbol_master=master_for(obj).key,
                position=Point(x=x, y=y),
            )
        )

    view = DrawingView(
        drawing_id="PID-DEMO-001",
        representations=reps,
    )

    routes: list[RouteRepresentation] = []
    for edge in model.connections:
        source = _anchor(model, view, edge.source.object_id, edge.source.port)
        target = _anchor(model, view, edge.target.object_id, edge.target.port)
        routes.append(
            RouteRepresentation(
                route_id=f"ROUTE-{edge.id}",
                semantic_edge_id=edge.id,
                line_style="signal" if edge.kind.value == "signal" else "process",
                points=_orthogonal(source, target),
            )
        )

    visible_associations = {
        "measures_pressure_at",
        "indicates_pressure_at",
        "measures_level_at",
        "indicates_level_at",
    }
    for edge in model.associations:
        if edge.relationship not in visible_associations:
            continue
        source_rep = view.representation_for(edge.subject_id)
        target_rep = view.representation_for(edge.target_id)
        routes.append(
            RouteRepresentation(
                route_id=f"ROUTE-{edge.id}",
                semantic_edge_id=edge.id,
                line_style="association",
                points=_orthogonal(source_rep.position, target_rep.position),
            )
        )

    view.routes = routes
    view.validate_against(model)
    return view
