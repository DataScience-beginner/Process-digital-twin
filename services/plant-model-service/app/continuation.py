from __future__ import annotations

from typing import Any


def continuation_section() -> dict[str, Any]:
    """Approved demo continuation used to prove multi-sheet P&ID mechanics.

    This section is intentionally separated from the current simulation-derived
    V-101/P-101 topology. A production project would publish its upstream PFD /
    simulation topology and configuration match before this section is compiled.
    """
    return {
        "section_id": "SEC-200",
        "configuration_id": "DOWNSTREAM_CONDITIONING_DEMO_V1",
        "configuration_status": "approved_demo_template",
        "drawing_id": "PID-DEMO-002",
        "title": "Downstream Conditioning / Product Separation",
        "incoming_reference": {
            "line_entity_id": "LINE-1103",
            "line_number": '6"-HC-1103-CS150',
            "from_drawing": "PID-DEMO-001",
            "from_connector": "TO-PROCESS",
            "to_drawing": "PID-DEMO-002",
            "to_connector": "FROM-PID-001",
        },
        "objects": [
            {
                "id": "EQ-E201",
                "tag": "E-201",
                "category": "equipment",
                "object_type": "process_cooler",
                "service": "Product Cooler",
            },
            {
                "id": "VLV-XV201",
                "tag": "XV-201",
                "category": "valve",
                "object_type": "isolation_valve",
                "service": "Cooler inlet isolation",
            },
            {
                "id": "INS-TI201",
                "tag": "TI-201",
                "category": "instrument",
                "object_type": "temperature_indicator",
                "service": "Cooler outlet temperature indication",
            },
            {
                "id": "EQ-V201",
                "tag": "V-201",
                "category": "equipment",
                "object_type": "vertical_separator",
                "service": "Product Separator",
            },
            {
                "id": "INS-LT201",
                "tag": "LT-201",
                "category": "instrument",
                "object_type": "level_transmitter",
                "service": "V-201 level measurement",
            },
            {
                "id": "INS-LIC201",
                "tag": "LIC-201",
                "category": "instrument",
                "object_type": "level_controller",
                "service": "V-201 level controller",
            },
            {
                "id": "VLV-LCV201",
                "tag": "LCV-201",
                "category": "valve",
                "object_type": "control_valve",
                "service": "V-201 liquid product level control",
            },
            {
                "id": "BOUND-PRODUCT201",
                "tag": "TO-PRODUCT",
                "category": "boundary",
                "object_type": "boundary",
                "service": "Liquid product battery limit",
            },
            {
                "id": "BOUND-VAPOR201",
                "tag": "TO-VAPOR-SYSTEM",
                "category": "boundary",
                "object_type": "boundary",
                "service": "Vapor product / recovery system",
            },
        ],
        "lines": [
            {
                "id": "LINE-1103",
                "line_number": '6"-HC-1103-CS150',
                "service": "P-101 discharge continuation to E-201",
                "from": "FROM-PID-001",
                "through": ["VLV-XV201", "EQ-E201", "INS-TI201"],
                "to": "EQ-V201",
                "continued_from": "PID-DEMO-001",
            },
            {
                "id": "LINE-1201",
                "line_number": '4"-HC-1201-CS150',
                "service": "V-201 liquid product",
                "from": "EQ-V201",
                "through": ["VLV-LCV201"],
                "to": "BOUND-PRODUCT201",
            },
            {
                "id": "LINE-1202",
                "line_number": '4"-VG-1202-CS150',
                "service": "V-201 vapor product",
                "from": "EQ-V201",
                "through": [],
                "to": "BOUND-VAPOR201",
            },
        ],
        "signals": [
            {
                "id": "SIGNAL-LT201-LIC201",
                "from": "INS-LT201",
                "to": "INS-LIC201",
                "service": "V-201 level measurement signal",
            },
            {
                "id": "SIGNAL-LIC201-LCV201",
                "from": "INS-LIC201",
                "to": "VLV-LCV201",
                "service": "V-201 level controller output",
            },
        ],
        "governance_note": (
            "Sheet 2 is an approved demo continuation template used to prove "
            "off-page continuity and multi-sheet representations. It is not "
            "claimed to be simulation-derived until the second-section PFD "
            "publisher and configuration matcher are extended."
        ),
    }
