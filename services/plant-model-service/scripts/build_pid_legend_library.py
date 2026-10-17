"""Create a PRIVATE, source-traceable engineering legend library from client PDF.

Example (never commit customer-derived results to GitHub)::

    python -m scripts.build_pid_legend_library inventory --pdf /secure/client.pdf \
        --legend-pages 38-58 --out /secure/client_library
    # inspect inventory.json, add symbols with approved dual reviewer evidence
    python -m scripts.build_pid_legend_library compile --pdf /secure/client.pdf \
        --manifest /secure/client_library/inventory.json --out /secure/client_library/compiled
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from app.pid_legend_library import create_inventory, compile_library, propose_glyph_rows


def _pages(spec: str) -> list[int]:
    parsed: list[int] = []
    for token in spec.split(","):
        tok = token.strip()
        if "-" in tok:
            start, end = (int(x) for x in tok.split("-", 1))
            if end < start: raise ValueError("Invalid page range")
            parsed.extend(range(start, end + 1))
        else: parsed.append(int(tok))
    if not parsed or any(i < 1 for i in parsed):
        raise ValueError("1-based positive legend pages required")
    return parsed


def main() -> None:
    p=argparse.ArgumentParser(description="Private PDF legend library inventory/compilation (NO P&ID matching)")
    s=p.add_subparsers(dest="command",required=True)
    a=s.add_parser("inventory");a.add_argument("--pdf",required=True);a.add_argument("--legend-pages",required=True);a.add_argument("--out",required=True)
    b=s.add_parser("compile");b.add_argument("--pdf",required=True);b.add_argument("--manifest",required=True);b.add_argument("--out",required=True)
    c=s.add_parser("propose-rows");c.add_argument("--pdf",required=True);c.add_argument("--page",type=int,required=True)
    c.add_argument("--glyph-x",required=True,help="glyph column x0,x1 in displayed PDF points")
    c.add_argument("--label-x",required=True,help="label column x0,x1 in displayed PDF points")
    c.add_argument("--y",required=True,help="y0,y1 range in displayed PDF points")
    c.add_argument("--prefix",default="CAND");c.add_argument("--out",required=True)
    x=p.parse_args();pdf=Path(x.pdf).read_bytes();out=Path(x.out);out.mkdir(parents=True,exist_ok=True)
    if x.command=="inventory":
        manifest=create_inventory(pdf,_pages(x.legend_pages),source_name=Path(x.pdf).name)
        (out/"inventory.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        print(f"Inventory created: {len(manifest['pages'])} legend pages; ZERO automatically approved symbols")
    elif x.command=="propose-rows":
        pair=lambda s:tuple(float(z) for z in s.split(","))
        result=propose_glyph_rows(pdf,x.page,pair(x.glyph_x),pair(x.label_x),pair(x.y),id_prefix=x.prefix)
        (out/f"{x.prefix}_proposals.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        print(f"{len(result)} unverified ink-row proposals; ZERO labels approved")
    else:
        manifest=json.loads(Path(x.manifest).read_text(encoding="utf-8"))
        print(json.dumps(compile_library(pdf,manifest,out),indent=2))

if __name__=="__main__":main()
