# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Structural health monitoring backend for the Merwede Bridge (Netherlands). Collects prism/TPS measurements from 9 pillars and 3 structural elements, computes displacements and rotations, and stores results in a Grafana-connected MySQL database.

## Running the Scripts

There is no build step or package manager config — the project is a collection of standalone Python scripts.

```bash
# Primary pipeline (runs on a schedule: every 4 hours at 00/04/08/12/16/20 UTC)
python main_brug/geomos_merwede.py

# Weather station sync (every 30 minutes)
python weerstations/geomos_weerstations.py

# Water level sync (hourly)
python waterlevel/geonius_waterlevel.py

# Ad-hoc report/visualization generation
python pijler_base_report.py
```

Install dependencies (no requirements.txt; infer from imports):
```bash
pip install pandas numpy matplotlib requests mysql-connector-python python-dotenv sqlalchemy shapely schedule
```

## Environment Configuration

Copy `.env` and populate with credentials:

```
GEOMOS_HOST=192.168.2.80
GEOMOS_PORT=8000
GEOMOS_API_KEY=...
GEOMOS_PROJECTID=1

GRAFANA_DB_HOST=100.81.211.62
GRAFANA_DB_PORT=3308
GRAFANA_DB_USER=root
GRAFANA_DB_PASSWORD=...
GRAFANA_DB_NAME=Merwedebrug_DIBEC
TABLE_NAME_MEASUREMENTS=measurements

ZERO_DATE=2025-12-02T15:00:00Z   # Reference epoch for null measurements
```

## Architecture

### Data Flow

```
Geomos API (prisms/TPS) ──► geomos_merwede.py ──► MySQL (Grafana)
Geonius API (water)     ──► geonius_waterlevel.py ──► MySQL
Weather Service API     ──► geomos_weerstations.py ──► MySQL
```

### Core Module: `main_brug/geomos_merwede.py`

This is the heart of the system. It contains two pillar classes and the full ETL pipeline:

- **`bridge_pillar_standard`** — used for Pijler 1, 2, 3, 5, 6, 7, 9, LandhoofdNoord, LandhoofdZuid. Expects 4 prisms (left/right × high/low). Calculates full displacement (Δx, Δy, Δz in mm) and rotation (rotX, rotY, rotZ in degrees).
- **`bridge_pillar_totalstation`** — used for Pijler4 and Pijler8. Only 2 TPS measurements; no rotY.

Each class takes `element_params` (from `brug_parameters.json`), `element_data` (the 4-hour block DataFrame), and `reference_data` (null measurements at `ZERO_DATE`).

### Bridge Parameters: `main_brug/brug_parameters.json`

Single source of truth for bridge geometry. For each of the 11 structural elements it stores:
- `prism_names` — identifiers to query from the Geomos API
- `prism_dist_constant` — horizontal distance between left/right prism pairs
- `opleg_data` — bearing (oplegging) positions: RD coordinates, z-offsets, interpolation distances

### Supporting Modules

| File | Purpose |
|---|---|
| `main_brug/calculating_brigde_element_average.py` | Aggregates raw measurements into the 4-hour block averages |
| `main_brug/point_exports.py` | Exports raw point data per block |
| `main_brug/raw_angles.py` | Processes TPS angle observations |
| `pijler_base_report.py` | Ad-hoc analysis: IQR outlier removal, displacement/rotation statistics, matplotlib plots |

### Coordinate Systems

All displacement calculations operate in two systems:
- **Local bridge frame** — origin at null point (2000, 5000), rotated 77.0737° relative to RD North
- **RD (Rijksdriehoeksmeting)** — Dutch national grid; used for bearing location output

Rotation matrices and interpolation between prism pairs are used to compute bearing (oplegging) displacements from prism measurements. The `shapely` `LineString`/`Point` API is used for linear interpolation along prism-to-prism baselines.

### Scheduling

Each script uses the `schedule` library with a blocking `while True` / `time.sleep(10)` poll loop. Logs are written daily to `logbook/log_DD_MM.txt`. CSV snapshots of raw and averaged results per 4-hour block are also written to `logbook/`.

### Database Schema (MySQL)

Key tables in `Merwedebrug_DIBEC`:
- `measurements` — raw prism coordinates per observation epoch
- `average_measurements` — 4-hourly aggregated coordinates
- `Pijler1`–`Pijler9`, `LandhoofdNoord`, `LandhoofdZuid`, `Basculekelder` — computed displacements/rotations per pillar
- `Oplegging_locaties` — bearing position outputs for Grafana panels
- `waterlevel`, `Weerstation1`, `Weerstation2` — sensor data

### Known Issues / Gotchas

- `geomos_merwede.py` line ~1110 has a hardcoded database name `"Duyen_testing_merwede"` that should use the env var.
- API authentication is via plain-text query parameters (`api_key=...`).
- The block-validity check requires ≥392 measurement points and a data span of ≥2 hours; blocks failing this are skipped with a log entry.
