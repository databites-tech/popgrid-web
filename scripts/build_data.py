"""
Build data/popgrid-data.js: every country x variable as popgrid block positions.

    python scripts/build_data.py              # all curated countries
    python scripts/build_data.py ESP DEU      # just these

Positions are in block units. Territories popgrid draws in a separate panel
(Canary Islands, Alaska, Hawaii, Svalbard) are moved next to the mainland, in
the corner that matches their real direction, so each country fits one frame
and every block can move between variables.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import pandas as pd
import popgrid
from popgrid import AreaGrid, PopGrid
from popgrid.data import REGION_LABELS, bundled_countries, gdp_quality, load_region_values
from popgrid.render import _classify_secondary, _group_panels_by_region

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "popgrid-data.js"
RES = Path(popgrid.__file__).parent / "resources"

# Four neutrals for popgrid's adjacency colouring; the site paints the two
# story regions blue and apricot on top.
NEUTRALS = ["#CBC1AE", "#B7AE9C", "#A49B8B", "#908879"]
GAP = 2  # blocks between the mainland and a parked territory
VARIABLES = ("population", "gdp")


def layout(g) -> list[tuple[float, float, str]]:
    """Block centres in block units (y grows downwards) with their region."""
    cs = g._cell_size
    lms = [lm for lm in g._landmasses if not lm["cells"].empty]
    main = lms[0]
    inline, panel = _classify_secondary(main, lms[1:], cs, panel_regions=g._panel_regions())
    panel = _group_panels_by_region(panel)

    base = pd.concat([lm["cells"] for lm in [main] + inline])
    bx, by = base["cx"] / cs, -base["cy"] / cs
    x0, x1, y0, y1 = bx.min(), bx.max(), by.min(), by.max()
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    out = list(zip(bx, by, base["region_name"]))

    cursor: dict[tuple[int, int], float] = {}
    for lm in sorted(panel, key=lambda l: -len(l["cells"])):
        c = lm["cells"]
        px, py = c["cx"] / cs, -c["cy"] / cs
        sx = -1 if px.mean() < mx else 1
        sy = -1 if py.mean() < my else 1
        w, h = px.max() - px.min() + 1, py.max() - py.min() + 1
        off = cursor.get((sx, sy), 0)
        tx = (x0 + off) if sx < 0 else (x1 - off - w + 1)
        ty = (y1 + GAP + 1) if sy > 0 else (y0 - GAP - h)
        cursor[(sx, sy)] = off + w + GAP
        dx, dy = tx - px.min(), ty - py.min()
        out += list(zip(px + dx, py + dy, c["region_name"]))
    return out


def first_source(csv_name: str, value_col: str) -> dict[str, str]:
    """{iso3: 'source, year'} from one of popgrid's bundled tables."""
    out: dict[str, str] = {}
    with open(RES / csv_name, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            src = row["source"] if row["year"] in row["source"] else f'{row["source"]}, {row["year"]}'
            out.setdefault(row["iso3"], src)
    return out


def build(iso: str, pop_src: dict, gdp_src: dict) -> dict:
    kw = dict(palette=NEUTRALS, color_mode="layouts")
    grids = {"land": AreaGrid(iso, **kw).build()}
    for v in VARIABLES:
        grids[v] = PopGrid(iso, by=v, **kw).build()

    a = grids["land"]
    names = sorted(a.color_map)
    idx = {n: i for i, n in enumerate(names)}
    disp = a._display_names() or {}
    parent = a._name_to_parent()
    land = {str(r.region_name): float(r.geometry.area) / 1e6 for r in a._regions_proj.itertuples()}
    values = {v: load_region_values(iso, names, by=v, name_to_parent=parent) for v in VARIABLES}

    layouts = {}
    for key, g in grids.items():
        flat: list[int] = []
        for x, y, r in layout(g):
            if r in idx:
                flat += [round(x * 10), round(y * 10), idx[r]]
        layouts[key] = flat

    return {
        "unit": REGION_LABELS.get(iso, "Regions"),
        "sources": {
            "population": pop_src.get(iso, "GHS-POP 2025 estimates"),
            "gdp": gdp_src.get(iso, "Kummu et al. gridded GDP PPP"),
        },
        "gdpQuality": gdp_quality(iso),
        "regions": [
            {
                "n": disp.get(n, n),
                "c": NEUTRALS.index(a.color_map[n]) if a.color_map[n] in NEUTRALS else 0,
                "land": round(land.get(n, 0)),
                "pop": int(values["population"].get(n, 0)),
                "gdp": int(values["gdp"].get(n, 0)),
            }
            for n in names
        ],
        "layouts": layouts,
    }


def main() -> None:
    countries = [c.upper() for c in sys.argv[1:]] or bundled_countries()
    data = {}
    if OUT.exists() and sys.argv[1:]:  # partial run: update the existing file
        txt = OUT.read_text(encoding="utf-8")
        data = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    pop_src = first_source("population.csv", "population")
    gdp_src = first_source("gdp.csv", "gdp")
    for iso in countries:
        t = time.time()
        try:
            data[iso] = build(iso, pop_src, gdp_src)
        except Exception as e:  # noqa: BLE001
            print(f"{iso}: failed ({e})", flush=True)
            continue
        lay = data[iso]["layouts"]
        print(f"{iso}: " + ", ".join(f"{k} {len(v) // 3}" for k, v in lay.items()) + f" blocks, {time.time() - t:.1f}s", flush=True)

    OUT.parent.mkdir(exist_ok=True)
    body = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    OUT.write_text(
        f"// Generated by scripts/build_data.py with popgrid {popgrid.__version__}. Do not edit.\n"
        f"window.POPGRID_DATA = {body};\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB, {len(data)} countries)")


if __name__ == "__main__":
    main()
