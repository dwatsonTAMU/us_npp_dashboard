# USA Nuclear Power Dashboard

Interactive dashboard displaying real-time status and regulatory activity for all 94 operating U.S. commercial nuclear reactors. Designed for embedding in WordPress via iframe.

**Texas A&M AESL Project**

## Features

- **Interactive Map**: Leaflet.js map with color-coded markers showing reactor performance
- **Multi-Unit Site Grouping**: Sites with multiple reactors displayed as single markers with unit count badges
- **Performance Metrics**: 30-day, 90-day, 365-day, and lifetime capacity factors
- **NRC ADAMS Integration**: Recent regulatory documents for each reactor
- **NRC Site Links**: Direct links to NRC info-finder pages for each reactor
- **Self-Contained HTML**: All dependencies embedded - works offline, no external requests
- **WordPress Ready**: Designed for iframe embedding

## Quick Start

```bash
# 1. Process reactor and capacity factor data
python3 process_data.py

# 2. Fetch ADAMS regulatory documents (optional - takes ~5 min)
python3 fetch_adams.py
python3 slim_adams.py

# 3. Build the dashboard
python3 build_dashboard.py

# 4. Serve locally for testing
python3 serve.py
# Visit http://localhost:8080
```

## Project Structure

```
plant_dashboard/
├── README.md                 # This file
├── index.html                # Output: Self-contained dashboard (500+ KB)
├── serve.py                  # Local HTTP server for testing
│
├── data/                     # Data files
│   ├── reactors_master.csv   # SOURCE: Master reactor data (edit this)
│   ├── reactors_master.json  # JSON version of master data
│   ├── reactors.json         # Processed reactor data with performance
│   ├── capacity_factors.json # Processed capacity factor metrics
│   ├── fleet_stats.json      # Fleet-wide statistics
│   ├── adams_activity.json   # Full ADAMS document data
│   ├── adams_activity_slim.json # Slimmed ADAMS data for dashboard
│   └── plant_news.json       # LLM-generated headlines (optional)
│
├── cache/                    # Cached external resources
│   ├── leaflet.css
│   ├── leaflet.js
│   └── us-states.json
│
├── process_data.py           # Processes master CSV + capacity factors
├── fetch_adams.py            # Fetches NRC ADAMS documents
├── slim_adams.py             # Slims ADAMS data for embedding
├── fetch_plant_news.py       # Fetches ADAMS + generates LLM headlines
├── generate_news_from_adams.py # Generates headlines from existing ADAMS
├── build_dashboard.py        # Builds self-contained HTML
│
└── nrc_reactor_status_unified_fixed.csv  # Daily capacity factor data
```

## Data Sources

### Master Reactor Data (`data/reactors_master.csv`)

The authoritative source for reactor information. Contains 94 reactors with:
- Name, docket number, license number
- Location, NRC region, coordinates
- Reactor type (PWR/BWR), containment type
- Capacity (MWe/MWt)
- License dates (original, renewed, expires)
- NRC site URLs

**To update reactor data**: Edit `data/reactors_master.csv` directly.

### Capacity Factor Data (`nrc_reactor_status_unified_fixed.csv`)

Daily power output data for all reactors. Format:
```
Date,Unit,Power
2024-01-01,Arkansas 1,100
2024-01-01,Arkansas 2,98
...
```

### NRC ADAMS API

Regulatory documents fetched via NRC's Web-Based ADAMS API:
- Sorted by publish date (most recent first)
- Filtered to plant-specific documents (<=5 dockets)
- Categories: LER, Inspection, Enforcement, License Amendment, Correspondence, Report

## Scripts

### `process_data.py`

Processes master reactor CSV and capacity factor data into optimized JSON.

**Input**:
- `data/reactors_master.csv`
- `nrc_reactor_status_unified_fixed.csv`

**Output**:
- `data/reactors.json` - Full reactor data with performance metrics
- `data/capacity_factors.json` - Capacity factor summaries
- `data/fleet_stats.json` - Fleet-wide statistics

**Metrics Calculated**:
- Current power level and status
- 30/90/365-day and lifetime capacity factors
- Outage tracking (count, days, days since)
- Monthly sparkline data
- Performance trend

### `fetch_adams.py`

Fetches recent NRC ADAMS documents for each reactor.

**Features**:
- Queries by docket number using 'starts' operator
- Sorts by PublishDatePARS descending (most recent first)
- Filters out industry-wide notices (>5 dockets)
- Concurrent requests (5 workers)

**Output**: `data/adams_activity.json`

### `slim_adams.py`

Reduces ADAMS data size for embedding in HTML.

**Input**: `data/adams_activity.json`
**Output**: `data/adams_activity_slim.json`

### `build_dashboard.py`

Builds self-contained HTML dashboard with all data and libraries embedded.

**Embeds**:
- Leaflet.js and CSS
- US states GeoJSON
- All reactor data
- ADAMS activity data
- Plant news (if available)

**Output**: `index.html` (~500 KB)

### `serve.py`

Simple HTTP server for local testing.

```bash
python3 serve.py
# Dashboard at http://localhost:8080
```

## Dashboard Features

### Map Markers

- **Color**: Based on 30-day capacity factor
  - Green (>=90%): Excellent
  - Light green (>=80%): Good
  - Yellow (>=70%): Fair
  - Orange (>=50%): Poor
  - Red (<50%): Critical
  - Gray: Offline/No data

- **Size**: Scaled by total site capacity
- **Badge**: Number of units at multi-unit sites
- **Glow**: Applied to sites with CF >= 95%

### Popup Details

Each reactor popup includes three tabs:
1. **Overview**: Current status, capacity factors, outage info
2. **Details**: License info, dates, operator, vendor
3. **News**: Recent ADAMS documents with links

### Filters

- Filter by NRC Region (1-4)
- Filter by Reactor Type (PWR/BWR)

### Statistics Panel

- Total reactors and sites
- Total capacity (GWe)
- Fleet capacity factor
- Reactors at full power

## API Reference

### NRC ADAMS API

Base URL: `https://adams.nrc.gov/wba/services/search/advanced/nrc`

Key parameters:
- `q`: Query in ADAMS format
- `s`: Sort field (e.g., `PublishDatePARS`)
- `so`: Sort order (`asc` or `desc`)
- `rows`: Number of results
- `start`: Offset for pagination

Example query for docket 05000482:
```
q=(mode:sections,sections:(filters:(public-library:!t),properties_search_all:!(!(DocketNumber,starts,'05000482',''))))
s=PublishDatePARS
so=desc
rows=10
```

## Phase 2: GitHub Pages Deployment

### Planned Steps

1. **Initialize Git Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Nuclear dashboard v1.0"
   ```

2. **Create GitHub Repository**
   - Create new repo on GitHub
   - Push local repository

3. **Configure GitHub Pages**
   - Settings > Pages > Source: main branch
   - Custom domain (optional)

4. **Automated Updates**
   - GitHub Actions workflow for daily data refresh
   - Cron job to fetch capacity factors and ADAMS data
   - Auto-rebuild and commit dashboard

### Proposed GitHub Actions Workflow

```yaml
name: Update Dashboard Data
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pandas requests openpyxl
      - run: python3 process_data.py
      - run: python3 fetch_adams.py
      - run: python3 slim_adams.py
      - run: python3 build_dashboard.py
      - run: |
          git config user.name 'GitHub Actions'
          git config user.email 'actions@github.com'
          git add -A
          git diff --staged --quiet || git commit -m "Auto-update dashboard data"
          git push
```

## Maintenance

### Adding a New Reactor

1. Add row to `data/reactors_master.csv` with all fields
2. Add NRC site code mapping in `process_data.py` if needed
3. Run `python3 process_data.py`
4. Run `python3 build_dashboard.py`

### Updating Capacity Factor Data

1. Replace/update `nrc_reactor_status_unified_fixed.csv`
2. Run `python3 process_data.py`
3. Run `python3 build_dashboard.py`

### Refreshing ADAMS Data

```bash
python3 fetch_adams.py
python3 slim_adams.py
python3 build_dashboard.py
```

## Technical Notes

### Docket Number Format

- Traditional reactors: `05000XXX` (e.g., `05000482` for Wolf Creek)
- COL reactors (Vogtle 3/4): `05200XXX` (e.g., `05200025` for Vogtle 3)

### Multi-Unit Site Detection

Sites are grouped by exact coordinate match. All units at a site must have identical latitude/longitude values in the master data.

### Performance Thresholds

- Full power: >= 95%
- Reduced power: >= 50%
- Low power: > 0%
- Offline: 0% or no data

### File Sizes

- Master CSV: ~34 KB
- Output HTML: ~500 KB
- ADAMS full: ~340 KB
- ADAMS slim: ~100 KB

## License

Texas A&M University - Advanced Energy Systems Laboratory

## Contact

For questions or issues, contact the AESL team.
