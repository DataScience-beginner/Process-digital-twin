from __future__ import annotations

from typing import Any


def build_demo_hazop() -> dict[str, Any]:
    """Deterministic HAZOP demonstrator linked to the current Digital BDEP graph.

    The rows are intentionally explicit and reviewable. They are workshop
    preparation data, not an automated replacement for a multidisciplinary
    HAZOP team.
    """
    nodes = [
        {
            "node_id": "HAZOP-NODE-01",
            "name": "V-101 Feed Separator",
            "design_intent": (
                "Separate incoming mixed hydrocarbon feed into vapor and liquid, "
                "maintain stable pressure/level, route liquid to P-101 and protect "
                "the vessel against credible overpressure."
            ),
            "entity_ids": [
                "EQ-V101",
                "VLV-PSV101",
                "INS-PT101",
                "INS-LT101",
                "INS-LIC101",
                "VLV-LCV101",
                "LINE-PSV101",
                "LINE-1102",
            ],
            "rows": [
                {
                    "row_id": "HZ-001",
                    "guideword": "MORE",
                    "parameter": "Pressure",
                    "deviation": "High pressure in V-101",
                    "causes": [
                        {
                            "text": "Blocked or restricted vapor outlet",
                            "entity_ids": ["EQ-V101", "LINE-PSV101"],
                        },
                        {
                            "text": "Upstream pressure/control failure",
                            "entity_ids": ["EQ-V101"],
                        },
                    ],
                    "consequences": [
                        "Vessel pressure can exceed intended operating envelope.",
                        "Potential loss of containment if relief/safeguarding is inadequate.",
                    ],
                    "safeguards": [
                        {
                            "text": "PT-101 pressure measurement / operator awareness",
                            "entity_ids": ["INS-PT101"],
                        },
                        {
                            "text": "PSV-101 overpressure protection",
                            "entity_ids": ["VLV-PSV101", "LINE-PSV101"],
                        },
                    ],
                    "linked_calculations": ["RELIEF-PSV101-BASIS"],
                    "recommendation": (
                        "Complete all relief scenarios and relief-header hydraulics; "
                        "retain relief engineer approval gate before issue."
                    ),
                    "status": "OPEN / PARTLY CALCULATED",
                    "risk": "High",
                },
                {
                    "row_id": "HZ-002",
                    "guideword": "MORE",
                    "parameter": "Level",
                    "deviation": "High liquid level in V-101",
                    "causes": [
                        {
                            "text": "LCV-101 fails closed or loses control output",
                            "entity_ids": ["VLV-LCV101", "INS-LIC101"],
                        },
                        {
                            "text": "P-101 unavailable / downstream liquid path blocked",
                            "entity_ids": ["EQ-P101", "LINE-1102"],
                        },
                    ],
                    "consequences": [
                        "Reduced vapor disengagement space.",
                        "Potential liquid carryover into vapor system.",
                        "Possible interaction with relief load and downstream equipment.",
                    ],
                    "safeguards": [
                        {
                            "text": "LT-101 / LIC-101 level control loop",
                            "entity_ids": ["INS-LT101", "INS-LIC101", "VLV-LCV101"],
                        }
                    ],
                    "linked_calculations": ["CALC-V101-HOLDUP"],
                    "recommendation": (
                        "Define LAH/LAHH and shutdown philosophy during safeguarding review; "
                        "verify required surge/response time."
                    ),
                    "status": "OPEN",
                    "risk": "Medium",
                },
                {
                    "row_id": "HZ-003",
                    "guideword": "LESS",
                    "parameter": "Level",
                    "deviation": "Low liquid level in V-101",
                    "causes": [
                        {
                            "text": "LCV-101 fails open / excessive liquid withdrawal",
                            "entity_ids": ["VLV-LCV101"],
                        },
                        {
                            "text": "Loss of feed",
                            "entity_ids": ["EQ-V101"],
                        },
                    ],
                    "consequences": [
                        "Gas blow-by to P-101 suction.",
                        "Pump loss of prime/cavitation and downstream instability.",
                    ],
                    "safeguards": [
                        {
                            "text": "LT-101 / LIC-101 continuous level control",
                            "entity_ids": ["INS-LT101", "INS-LIC101"],
                        }
                    ],
                    "linked_calculations": ["CALC-V101-HOLDUP", "CALC-P101-RATED-FLOW"],
                    "recommendation": "Define LAL/LALL and pump trip permissive in safeguarding narrative.",
                    "status": "OPEN",
                    "risk": "Medium",
                },
            ],
        },
        {
            "node_id": "HAZOP-NODE-02",
            "name": "P-101 Suction / Pump / Discharge",
            "design_intent": (
                "Transfer V-101 liquid to downstream process at the published rated "
                "flow/head while maintaining adequate suction conditions and preventing "
                "reverse flow."
            ),
            "entity_ids": [
                "EQ-P101",
                "LINE-1102",
                "LINE-1103",
                "VLV-XV101",
                "VLV-NRV101",
                "VLV-XV102",
                "INS-PI101S",
                "INS-PI101D",
            ],
            "rows": [
                {
                    "row_id": "HZ-101",
                    "guideword": "NO",
                    "parameter": "Flow",
                    "deviation": "No forward liquid flow through P-101",
                    "causes": [
                        {
                            "text": "XV-101 or XV-102 closed / line blocked",
                            "entity_ids": ["VLV-XV101", "VLV-XV102", "LINE-1102", "LINE-1103"],
                        },
                        {
                            "text": "P-101 trip / mechanical failure",
                            "entity_ids": ["EQ-P101"],
                        },
                    ],
                    "consequences": [
                        "V-101 liquid level rises.",
                        "Loss of downstream feed.",
                        "Pump may operate at shutoff if discharge is blocked.",
                    ],
                    "safeguards": [
                        {
                            "text": "PI-101S / PI-101D enable differential-pressure indication",
                            "entity_ids": ["INS-PI101S", "INS-PI101D"],
                        },
                        {
                            "text": "Minimum-flow recycle loop provides low-flow protection when available",
                            "entity_ids": ["INS-FT101", "INS-FIC101", "VLV-FCV101", "LINE-1190"],
                        },
                    ],
                    "linked_calculations": ["CALC-P101-RATED-FLOW", "LINE-1102-SIZING", "LINE-1103-SIZING"],
                    "recommendation": "Confirm trip/permissive philosophy and blocked-discharge protection basis.",
                    "status": "OPEN",
                    "risk": "Medium",
                },
                {
                    "row_id": "HZ-102",
                    "guideword": "REVERSE",
                    "parameter": "Flow",
                    "deviation": "Reverse flow from downstream toward P-101",
                    "causes": [
                        {
                            "text": "P-101 stopped with downstream system pressurized",
                            "entity_ids": ["EQ-P101", "LINE-1103"],
                        },
                        {
                            "text": "NRV-101 fails open / leaks significantly",
                            "entity_ids": ["VLV-NRV101"],
                        },
                    ],
                    "consequences": [
                        "Reverse rotation / mechanical damage risk.",
                        "Backflow toward V-101 depending on isolation/control-valve positions.",
                    ],
                    "safeguards": [
                        {
                            "text": "NRV-101 check valve",
                            "entity_ids": ["VLV-NRV101"],
                        }
                    ],
                    "linked_calculations": [],
                    "recommendation": "Confirm check-valve reliability requirement and isolation philosophy.",
                    "status": "OPEN",
                    "risk": "Medium",
                },
                {
                    "row_id": "HZ-103",
                    "guideword": "LESS",
                    "parameter": "Suction pressure",
                    "deviation": "Low P-101 suction pressure / inadequate NPSH margin",
                    "causes": [
                        {
                            "text": "Low V-101 level",
                            "entity_ids": ["EQ-V101", "INS-LT101"],
                        },
                        {
                            "text": "Suction line restriction / XV-101 partially closed",
                            "entity_ids": ["LINE-1102", "VLV-XV101"],
                        },
                    ],
                    "consequences": [
                        "Cavitation, vibration and reduced pump performance.",
                        "Potential loss of flow and equipment damage.",
                    ],
                    "safeguards": [
                        {
                            "text": "PI-101S local suction pressure indication",
                            "entity_ids": ["INS-PI101S"],
                        }
                    ],
                    "linked_calculations": ["CALC-P101-RATED-FLOW", "LINE-1102-SIZING"],
                    "recommendation": (
                        "Complete NPSHA/system hydraulic calculation and define low-suction "
                        "pressure / low-level protective action."
                    ),
                    "status": "GATED BY HYDRAULICS",
                    "risk": "High",
                },
            ],
        },
        {
            "node_id": "HAZOP-NODE-03",
            "name": "P-101 Minimum-Flow Recycle",
            "design_intent": (
                "Maintain P-101 above its minimum continuous flow by recycling liquid "
                "from discharge back to V-101 through FT-101 / FIC-101 / FCV-101."
            ),
            "entity_ids": [
                "LINE-1190",
                "INS-FT101",
                "INS-FIC101",
                "VLV-FCV101",
                "EQ-P101",
                "EQ-V101",
            ],
            "rows": [
                {
                    "row_id": "HZ-201",
                    "guideword": "NO",
                    "parameter": "Recycle flow",
                    "deviation": "No minimum-flow recycle when required",
                    "causes": [
                        {
                            "text": "FCV-101 fails closed / actuator or signal failure",
                            "entity_ids": ["VLV-FCV101", "INS-FIC101"],
                        },
                        {
                            "text": "Recycle line blocked",
                            "entity_ids": ["LINE-1190"],
                        },
                    ],
                    "consequences": [
                        "P-101 can operate below minimum continuous flow.",
                        "Temperature rise, vibration or internal recirculation damage risk.",
                    ],
                    "safeguards": [
                        {
                            "text": "FCV-101 specified fail-open",
                            "entity_ids": ["VLV-FCV101"],
                        },
                        {
                            "text": "FT-101 / FIC-101 minimum-flow control",
                            "entity_ids": ["INS-FT101", "INS-FIC101"],
                        },
                    ],
                    "linked_calculations": ["CALC-FCV101-CV", "LINE-1190-SIZING"],
                    "recommendation": "Confirm low-flow alarm/trip philosophy and valve fail-action energy state.",
                    "status": "OPEN",
                    "risk": "High",
                },
                {
                    "row_id": "HZ-202",
                    "guideword": "MORE",
                    "parameter": "Recycle flow",
                    "deviation": "Excessive recycle flow",
                    "causes": [
                        {
                            "text": "FCV-101 fails fully open / controller output high",
                            "entity_ids": ["VLV-FCV101", "INS-FIC101"],
                        }
                    ],
                    "consequences": [
                        "Reduced net downstream flow.",
                        "Increased pump power and possible V-101 thermal/hydraulic disturbance.",
                    ],
                    "safeguards": [
                        {
                            "text": "FT-101 flow measurement and FIC-101 control",
                            "entity_ids": ["INS-FT101", "INS-FIC101"],
                        }
                    ],
                    "linked_calculations": ["CALC-FCV101-CV"],
                    "recommendation": "Verify control range, maximum opening and operator alarm requirements.",
                    "status": "OPEN",
                    "risk": "Low / Medium",
                },
            ],
        },
    ]

    return {
        "title": "Digital BDEP HAZOP Demonstrator",
        "status": "workshop_preparation_demo",
        "governance_note": (
            "The Digital Thread pre-populates design intent, connected causes, safeguards "
            "and calculation references. HAZOP decisions, risk ranking and action closure "
            "remain the responsibility of the multidisciplinary HAZOP team."
        ),
        "nodes": nodes,
    }


def hazop_rows_for_entity(entity_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in build_demo_hazop()["nodes"]:
        for row in node["rows"]:
            linked = entity_id in node["entity_ids"]
            if not linked:
                linked = any(
                    entity_id in item.get("entity_ids", [])
                    for item in [*row["causes"], *row["safeguards"]]
                )
            if linked:
                rows.append(
                    {
                        "node_id": node["node_id"],
                        "node_name": node["name"],
                        **row,
                    }
                )
    return rows
