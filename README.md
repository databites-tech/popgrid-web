# popgrid-web

Explore countries as [popgrid](https://github.com/databites-tech/popgrid) block maps. Every map has about 1,000 equal blocks. Switch between land, population and GDP and every block moves to the region that owns that share.

The site is static: one `index.html` plus one generated data file. No framework, no build step for the page itself.

## Run it locally

Open `index.html` in a browser. That's it: the data loads as a script, so it works straight from disk.

## Rebuild the data

The layouts come from popgrid 0.7.0 or later (GDP support).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # or: pip install -e ../popgrid

python scripts/build_data.py             # all curated countries, a few minutes
python scripts/build_data.py ESP DEU     # rebuild only these, keep the rest
```

This writes `data/popgrid-data.js`. Commit it: the site serves it as is.

## What the data file holds

For each country: its regions (name, land km², population, GDP, colour index) and one layout per variable. A layout is a flat list of `x*10, y*10, regionIndex` triples, in block units. Territories popgrid draws in a separate panel (Canary Islands, Alaska, Hawaii, Svalbard) are parked next to the mainland so every block can move between variables.

## Add a variable

1. Add it to popgrid (`PopGrid(iso, by="...")`).
2. Add its key to `VARIABLES` in `scripts/build_data.py` and to `VARS` in `index.html`, plus its headline and dek lines in `updateText()`.
3. Rebuild the data.

## Deploy

Cloudflare Pages, no build command, output directory `/`. Point `popgrid.databites.tech` at it.

## Sources

- Boundaries: Natural Earth admin-1 (1:10m)
- Population: national statistics offices, curated in popgrid
- GDP: Kummu et al. 2025, gridded GDP PPP (CC BY 4.0); regional splits marked "modelled" where a country reports no regional GDP

Made by [Josep Ferrer](https://databites.tech). MIT licence.
