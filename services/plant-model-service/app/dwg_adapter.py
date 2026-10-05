from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path


class DwgConverterUnavailable(RuntimeError):
    pass


def dwg_converter_status() -> dict[str, str | bool]:
    command = os.getenv("DWG_CONVERTER_CMD", "").strip()
    return {
        "configured": bool(command),
        "mode": "external_approved_converter",
        "command_template": command if command else "NOT_CONFIGURED",
        "input_format": "DXF",
        "output_format": "DWG",
        "note": (
            "Configure DWG_CONVERTER_CMD with an approved Autodesk/ODA converter "
            "command template containing {input} and {output}. The Digital BDEP "
            "service never fabricates a DWG file."
        ),
    }


def convert_dxf_to_dwg(dxf_bytes: bytes) -> bytes:
    """Convert DXF to DWG using an administrator-configured local converter.

    Example configuration:
      DWG_CONVERTER_CMD="/opt/oda/convert {input} {output}"

    The command is tokenized with shlex and executed without a shell.
    """
    template = os.getenv("DWG_CONVERTER_CMD", "").strip()
    if not template:
        raise DwgConverterUnavailable(
            "DWG converter is not configured. Export DXF now or configure the "
            "approved Autodesk/ODA converter adapter."
        )
    if "{input}" not in template or "{output}" not in template:
        raise DwgConverterUnavailable(
            "DWG_CONVERTER_CMD must contain both {input} and {output} placeholders."
        )

    with tempfile.TemporaryDirectory(prefix="digital-bdep-dwg-") as tempdir:
        root = Path(tempdir)
        source = root / "drawing.dxf"
        target = root / "drawing.dwg"
        source.write_bytes(dxf_bytes)

        args = [
            token.replace("{input}", str(source)).replace("{output}", str(target))
            for token in shlex.split(template)
        ]
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode != 0:
            raise DwgConverterUnavailable(
                "Configured DWG converter failed: "
                + (completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}")
            )
        if not target.exists() or target.stat().st_size == 0:
            raise DwgConverterUnavailable(
                "Configured DWG converter completed but produced no DWG file."
            )
        return target.read_bytes()
