#!/usr/bin/env python3
"""
Dashboard Builder - Creates a self-contained HTML file with all data embedded.
No external dependencies - works offline.
"""

import json
import os
import requests
from datetime import datetime

BASE_DIR = "/home/dwatson/projects/plant_dashboard"
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
OUTPUT_FILE = os.path.join(BASE_DIR, "index.html")

os.makedirs(CACHE_DIR, exist_ok=True)

def load_json(filename):
    """Load JSON file from data directory."""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def fetch_and_cache(url, filename):
    """Fetch a URL and cache it locally."""
    cache_path = os.path.join(CACHE_DIR, filename)

    # Check cache first
    if os.path.exists(cache_path):
        print(f"  Using cached: {filename}")
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()

    # Fetch from URL
    print(f"  Fetching: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text

        # Save to cache
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return content
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return ""

def build_html():
    """Build the self-contained HTML dashboard."""

    # Load all data
    print("Loading data files...")
    reactors = load_json('reactors.json')
    fleet_stats = load_json('fleet_stats.json')
    plant_news = load_json('plant_news.json')

    print(f"  Reactors: {len(reactors)}")
    print(f"  News dockets: {len(plant_news.get('by_docket', {}))}")

    # Convert to JSON strings for embedding
    reactors_json = json.dumps(reactors)
    fleet_stats_json = json.dumps(fleet_stats)
    plant_news_json = json.dumps(plant_news)

    # Fetch external libraries
    print("\nFetching external libraries...")
    leaflet_css = fetch_and_cache(
        'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
        'leaflet.css'
    )
    leaflet_js = fetch_and_cache(
        'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
        'leaflet.js'
    )
    us_states_geojson = fetch_and_cache(
        'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json',
        'us-states.json'
    )

    version = datetime.now().strftime("%Y%m%d%H%M")

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <title>USA Nuclear Power Dashboard | Texas A&M AESL</title>
    <!-- Version: {version} -->
    <style>
        /* Using system fonts for self-contained HTML */

        :root {{
            --tamu-maroon: #500000;
            --tamu-maroon-light: #7d0000;
            --tamu-maroon-dark: #3b0000;
            --accent-gold: #ffb81c;
            --bg-light: #f8f9fa;
            --bg-white: #ffffff;
            --text-dark: #1a1a1a;
            --text-muted: #666666;
            --border-color: #e0e0e0;
            --shadow-sm: 0 2px 4px rgba(80, 0, 0, 0.08);
            --shadow-md: 0 4px 12px rgba(80, 0, 0, 0.12);
            --shadow-lg: 0 8px 24px rgba(80, 0, 0, 0.16);
            --perf-excellent: #22c55e;
            --perf-good: #84cc16;
            --perf-fair: #eab308;
            --perf-poor: #f97316;
            --perf-critical: #ef4444;
            --perf-offline: #6b7280;
        }}

        .dark-mode {{
            --tamu-maroon: #7d0000;
            --tamu-maroon-light: #a00000;
            --bg-light: #1a1a1a;
            --bg-white: #2d2d2d;
            --text-dark: #e0e0e0;
            --text-muted: #a0a0a0;
            --border-color: #404040;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-light);
            color: var(--text-dark);
            overflow-x: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, var(--tamu-maroon) 0%, var(--tamu-maroon-dark) 100%);
            color: white;
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .header h1 {{
            font-size: 1.5rem;
            font-weight: 700;
        }}

        .header-controls {{
            display: flex;
            gap: 0.75rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        .search-input {{
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 0.4rem 0.75rem;
            border-radius: 4px;
            font-size: 0.85rem;
            width: 200px;
        }}

        .search-input::placeholder {{ color: rgba(255,255,255,0.7); }}

        .header-btn {{
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 0.4rem 0.75rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .header-btn:hover {{ background: rgba(255,255,255,0.25); }}

        .stats-bar {{
            display: flex;
            gap: 1.5rem;
            padding: 0.75rem 1.5rem;
            background: var(--bg-white);
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
        }}

        .stat-item {{ display: flex; flex-direction: column; gap: 0.1rem; }}

        .stat-value {{
            font-family: 'SF Mono', 'Monaco', 'Consolas', 'Liberation Mono', monospace;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--tamu-maroon);
        }}

        .stat-label {{
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .main-container {{
            display: flex;
            height: calc(100vh - 120px);
        }}

        .sidebar {{
            width: 280px;
            background: var(--bg-white);
            border-right: 1px solid var(--border-color);
            overflow-y: auto;
            padding: 1rem;
        }}

        .sidebar-section {{
            margin-bottom: 1.25rem;
        }}

        .sidebar-title {{
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--tamu-maroon);
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}

        .filter-select {{
            width: 100%;
            padding: 0.4rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        }}

        .status-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.4rem;
        }}

        .status-item {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.4rem;
            background: var(--bg-light);
            border-radius: 4px;
            font-size: 0.8rem;
        }}

        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}

        .status-dot.full {{ background: var(--perf-excellent); }}
        .status-dot.reduced {{ background: var(--perf-fair); }}
        .status-dot.low {{ background: var(--perf-poor); }}
        .status-dot.offline {{ background: var(--perf-critical); }}

        .performer-list {{ list-style: none; }}

        .performer-item {{
            display: flex;
            justify-content: space-between;
            padding: 0.4rem 0;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.8rem;
            cursor: pointer;
        }}

        .performer-item:hover {{ background: var(--bg-light); }}

        .map-container {{
            flex: 1;
            position: relative;
        }}

        #map {{
            width: 100%;
            height: 100%;
            background: #e8eef2;
        }}

        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }}

        .legend {{
            position: absolute;
            bottom: 1rem;
            right: 1rem;
            background: var(--bg-white);
            padding: 0.75rem;
            border-radius: 6px;
            box-shadow: var(--shadow-md);
            z-index: 1000;
            font-size: 0.75rem;
        }}

        .legend-title {{
            font-size: 0.65rem;
            text-transform: uppercase;
            color: var(--tamu-maroon);
            font-weight: 600;
            margin-bottom: 0.4rem;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            margin-bottom: 0.25rem;
        }}

        .legend-marker {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }}

        /* Leaflet popup styles */
        .leaflet-popup-content-wrapper {{
            border-radius: 8px;
            padding: 0;
        }}

        .leaflet-popup-content {{
            margin: 0;
            width: 360px !important;
        }}

        .popup-header {{
            background: linear-gradient(135deg, var(--tamu-maroon), var(--tamu-maroon-light));
            color: white;
            padding: 0.75rem 1rem;
        }}

        .popup-name {{
            font-size: 1.1rem;
            font-weight: 700;
        }}

        .popup-location {{
            font-size: 0.75rem;
            opacity: 0.9;
        }}

        .popup-status {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 3px;
            font-size: 0.65rem;
            font-weight: 700;
            margin-top: 0.4rem;
        }}

        .popup-status.online {{ background: var(--perf-excellent); }}
        .popup-status.reduced {{ background: var(--perf-fair); color: #000; }}
        .popup-status.offline {{ background: var(--perf-critical); }}

        .popup-tabs {{
            display: flex;
            background: var(--bg-light);
            border-bottom: 1px solid var(--border-color);
        }}

        .popup-tab {{
            flex: 1;
            padding: 0.5rem;
            text-align: center;
            font-size: 0.7rem;
            font-weight: 600;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            color: var(--text-muted);
        }}

        .popup-tab:hover {{ color: var(--tamu-maroon); }}
        .popup-tab.active {{
            color: var(--tamu-maroon);
            border-bottom-color: var(--tamu-maroon);
            background: var(--bg-white);
        }}

        .popup-content {{
            padding: 0.75rem;
            max-height: 280px;
            overflow-y: auto;
            display: none;
        }}

        .popup-content.active {{ display: block; }}

        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.4rem;
        }}

        .info-item {{
            background: var(--bg-light);
            padding: 0.5rem;
            border-radius: 4px;
            border-left: 3px solid var(--tamu-maroon);
        }}

        .info-label {{
            font-size: 0.6rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }}

        .info-value {{
            font-family: 'SF Mono', 'Monaco', 'Consolas', 'Liberation Mono', monospace;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .news-item {{
            padding: 0.5rem;
            background: var(--bg-light);
            border-radius: 4px;
            margin-bottom: 0.4rem;
            border-left: 3px solid var(--accent-gold);
        }}

        .news-date {{
            font-size: 0.65rem;
            color: var(--text-muted);
        }}

        .news-headline {{
            font-size: 0.8rem;
            font-weight: 600;
            margin: 0.2rem 0;
        }}

        .news-link {{
            font-size: 0.7rem;
            color: var(--tamu-maroon);
        }}

        .unit-card {{
            background: var(--bg-light);
            padding: 0.5rem;
            border-radius: 4px;
            margin-bottom: 0.4rem;
            border-left: 3px solid var(--tamu-maroon-light);
        }}

        .unit-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.3rem;
        }}

        .unit-name {{ font-weight: 600; font-size: 0.85rem; color: var(--tamu-maroon); }}

        .unit-badge {{
            background: var(--tamu-maroon);
            color: white;
            padding: 0.1rem 0.4rem;
            border-radius: 3px;
            font-size: 0.65rem;
            font-weight: 600;
        }}

        .unit-metrics {{
            display: flex;
            gap: 0.75rem;
            font-size: 0.7rem;
        }}

        .cf-high {{ color: var(--perf-excellent); }}
        .cf-low {{ color: var(--perf-critical); }}

        .custom-marker {{
            border: 2px solid white;
            border-radius: 50%;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 9px;
            font-weight: 700;
            color: white;
            cursor: pointer;
        }}

        .custom-marker:hover {{ transform: scale(1.2); }}
        .custom-marker.excellent {{ background: var(--perf-excellent); }}
        .custom-marker.good {{ background: var(--perf-good); }}
        .custom-marker.fair {{ background: var(--perf-fair); }}
        .custom-marker.poor {{ background: var(--perf-poor); }}
        .custom-marker.critical {{ background: var(--perf-critical); }}
        .custom-marker.offline {{ background: var(--perf-offline); }}

        .custom-marker.glow {{
            animation: glow 2s ease-in-out infinite;
        }}

        @keyframes glow {{
            0%, 100% {{ box-shadow: 0 0 5px var(--perf-excellent), 0 2px 6px rgba(0,0,0,0.3); }}
            50% {{ box-shadow: 0 0 15px var(--perf-excellent), 0 0 25px var(--perf-excellent); }}
        }}

        .footer {{
            background: var(--bg-white);
            border-top: 1px solid var(--border-color);
            padding: 0.5rem 1.5rem;
            font-size: 0.7rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
        }}

        .footer a {{ color: var(--tamu-maroon); text-decoration: none; margin-left: 0.75rem; }}
        .footer a:hover {{ text-decoration: underline; }}

        @media (max-width: 768px) {{
            .sidebar {{ display: none; }}
            .header h1 {{ font-size: 1.2rem; }}
            .stats-bar {{ gap: 0.75rem; padding: 0.5rem 1rem; }}
            .stat-value {{ font-size: 1rem; }}
            .leaflet-popup-content {{ width: 280px !important; }}
        }}
    </style>

    <!-- Leaflet CSS (embedded) -->
    <style>
    {leaflet_css}
    </style>
</head>
<body>
    <header class="header">
        <div>
            <div style="font-size:0.65rem;opacity:0.9;letter-spacing:1px;">TEXAS A&M AESL</div>
            <h1>USA Nuclear Power Dashboard</h1>
        </div>
        <div class="header-controls">
            <input type="text" class="search-input" id="search" placeholder="Search plants...">
            <button class="header-btn" id="dark-toggle">Dark Mode</button>
        </div>
    </header>

    <div class="stats-bar">
        <div class="stat-item">
            <div class="stat-value" id="s-reactors">--</div>
            <div class="stat-label">Reactors</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="s-capacity">--</div>
            <div class="stat-label">GWe Capacity</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="s-cf">--</div>
            <div class="stat-label">Fleet CF (90d)</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="s-pwr">--</div>
            <div class="stat-label">PWR</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="s-bwr">--</div>
            <div class="stat-label">BWR</div>
        </div>
    </div>

    <div class="main-container">
        <aside class="sidebar">
            <div class="sidebar-section">
                <div class="sidebar-title">Filters</div>
                <select class="filter-select" id="f-region">
                    <option value="">All Regions</option>
                    <option value="1">Region I (Northeast)</option>
                    <option value="2">Region II (Southeast)</option>
                    <option value="3">Region III (Midwest)</option>
                    <option value="4">Region IV (West)</option>
                </select>
                <select class="filter-select" id="f-type">
                    <option value="">All Types</option>
                    <option value="PWR">PWR Only</option>
                    <option value="BWR">BWR Only</option>
                </select>
            </div>

            <div class="sidebar-section">
                <div class="sidebar-title">Current Status</div>
                <div class="status-grid">
                    <div class="status-item"><div class="status-dot full"></div><span id="st-full">--</span> Full</div>
                    <div class="status-item"><div class="status-dot reduced"></div><span id="st-reduced">--</span> Reduced</div>
                    <div class="status-item"><div class="status-dot low"></div><span id="st-low">--</span> Low</div>
                    <div class="status-item"><div class="status-dot offline"></div><span id="st-offline">--</span> Offline</div>
                </div>
            </div>

            <div class="sidebar-section">
                <div class="sidebar-title">Top Performers (365d)</div>
                <ul class="performer-list" id="top-list"></ul>
            </div>

            <div class="sidebar-section">
                <div class="sidebar-title">Lowest Performers</div>
                <ul class="performer-list" id="bottom-list"></ul>
            </div>
        </aside>

        <div class="map-container">
            <div id="map">
                <div class="loading">Loading map...</div>
            </div>
            <div class="legend">
                <div class="legend-title">Performance (30d CF)</div>
                <div class="legend-item"><div class="legend-marker" style="background:var(--perf-excellent)"></div> >90%</div>
                <div class="legend-item"><div class="legend-marker" style="background:var(--perf-good)"></div> 80-90%</div>
                <div class="legend-item"><div class="legend-marker" style="background:var(--perf-fair)"></div> 70-80%</div>
                <div class="legend-item"><div class="legend-marker" style="background:var(--perf-poor)"></div> 50-70%</div>
                <div class="legend-item"><div class="legend-marker" style="background:var(--perf-critical)"></div> <50%</div>
            </div>
        </div>
    </div>

    <footer class="footer">
        <div>Data: NRC | Updated: <span id="update-date">--</span></div>
        <div>
            <a href="https://www.nrc.gov/reactors/operating.html" target="_blank">NRC Reactor List</a>
            <a href="https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/" target="_blank">Status Reports</a>
        </div>
    </footer>

    <!-- Leaflet JS (embedded) -->
    <script>
    {leaflet_js}
    </script>

    <script>
    // Embedded data
    const reactorData = {reactors_json};
    const fleetStats = {fleet_stats_json};
    const plantNews = {plant_news_json};
    const usStatesGeoJSON = {us_states_geojson};

    let map, markers = [];
    let filters = {{ region: '', type: '' }};

    function init() {{
        initMap();
        updateStats();
        updateSidebar();
        setupEvents();
    }}

    function initMap() {{
        map = L.map('map').setView([39.8, -98.6], 5);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap'
        }}).addTo(map);

        // Add state boundaries (embedded)
        if (usStatesGeoJSON) {{
            L.geoJSON(usStatesGeoJSON, {{
                style: {{ color: '#500000', weight: 1.5, opacity: 0.3, fill: false }}
            }}).addTo(map);
        }}

        updateMarkers();
    }}

    function getBaseName(name) {{
        return name.replace(/,?\\s*(Unit\\s*)?\\d+$/i, '').trim();
    }}

    function groupBySite(reactors) {{
        const sites = {{}};
        reactors.forEach(r => {{
            if (!r.coordinates) return;
            const key = `${{r.coordinates.latitude}},${{r.coordinates.longitude}}`;
            if (!sites[key]) {{
                sites[key] = {{
                    name: getBaseName(r.name),
                    location: r.location,
                    coords: r.coordinates,
                    units: []
                }};
            }}
            sites[key].units.push(r);
        }});
        return Object.values(sites);
    }}

    function getPerfClass(cf) {{
        if (cf == null) return 'offline';
        if (cf >= 90) return 'excellent';
        if (cf >= 80) return 'good';
        if (cf >= 70) return 'fair';
        if (cf >= 50) return 'poor';
        return 'critical';
    }}

    function getSitePerf(units) {{
        // Use 30-day capacity factor for coloring (less aggressive than 90-day)
        const cfs = units.filter(u => u.performance?.capacity_factor_30d != null)
                        .map(u => u.performance.capacity_factor_30d);
        return cfs.length ? cfs.reduce((a,b) => a+b) / cfs.length : null;
    }}

    function getSiteStatus(units) {{
        const statuses = units.map(u => u.performance?.status || 'offline');
        if (statuses.includes('full_power')) return 'full_power';
        if (statuses.includes('reduced_power')) return 'reduced_power';
        if (statuses.includes('low_power')) return 'low_power';
        return 'offline';
    }}

    function updateMarkers() {{
        markers.forEach(m => map.removeLayer(m));
        markers = [];

        let filtered = reactorData.filter(r => {{
            if (filters.region && r.nrc_region != filters.region) return false;
            if (filters.type && r.reactor_type != filters.type) return false;
            return true;
        }});

        const sites = groupBySite(filtered);

        sites.forEach(site => {{
            const cf = getSitePerf(site.units);
            const perfClass = getPerfClass(cf);
            const isHigh = cf != null && cf >= 95;
            const totalCap = site.units.reduce((s,u) => s + (u.capacity_mwe || 0), 0);
            const size = Math.round(14 * Math.min(1 + totalCap/4000, 1.4));

            const icon = L.divIcon({{
                html: `<div class="custom-marker ${{perfClass}} ${{isHigh ? 'glow' : ''}}" style="width:${{size}}px;height:${{size}}px">${{site.units.length > 1 ? site.units.length : ''}}</div>`,
                className: '',
                iconSize: [size, size],
                iconAnchor: [size/2, size/2]
            }});

            const marker = L.marker([site.coords.latitude, site.coords.longitude], {{ icon }}).addTo(map);
            marker.bindPopup(() => createPopup(site), {{ maxWidth: 400 }});
            marker.bindTooltip(`${{site.name}}<br>CF: ${{cf != null ? cf.toFixed(1) + '%' : 'N/A'}}`);
            markers.push(marker);
        }});
    }}

    function createPopup(site) {{
        const cf = getSitePerf(site.units);
        const status = getSiteStatus(site.units);
        const statusLabel = {{ full_power: 'ONLINE', reduced_power: 'REDUCED', low_power: 'LOW POWER', offline: 'OFFLINE' }}[status];
        const statusClass = status === 'full_power' ? 'online' : status === 'offline' ? 'offline' : 'reduced';
        const unit = site.units[0];
        const totalCap = site.units.reduce((s,u) => s + (u.capacity_mwe || 0), 0);

        const unitsHtml = site.units.map(u => {{
            const p = u.performance || {{}};
            return `<div class="unit-card">
                <div class="unit-header">
                    <span class="unit-name">${{u.name}}</span>
                    <span class="unit-badge">${{u.reactor_type}}</span>
                </div>
                <div class="unit-metrics">
                    <span>Power: ${{p.current_power || 0}}%</span>
                    <span class="${{getPerfClass(p.capacity_factor_90d) === 'excellent' ? 'cf-high' : getPerfClass(p.capacity_factor_90d) === 'critical' ? 'cf-low' : ''}}">CF(90d): ${{p.capacity_factor_90d != null ? p.capacity_factor_90d.toFixed(1) + '%' : 'N/A'}}</span>
                </div>
            </div>`;
        }}).join('');

        // Get news for this plant
        const newsHtml = getNewsHtml(site.units);

        return `<div class="popup-header">
            <div class="popup-name">${{site.name}}</div>
            <div class="popup-location">${{site.location || ''}}</div>
            <span class="popup-status ${{statusClass}}">${{statusLabel}}</span>
        </div>
        <div class="popup-tabs">
            <div class="popup-tab active" onclick="switchTab(this, 'overview')">Overview</div>
            <div class="popup-tab" onclick="switchTab(this, 'news')">News</div>
            <div class="popup-tab" onclick="switchTab(this, 'details')">Details</div>
        </div>
        <div class="popup-content active" id="tab-overview">
            <div class="info-grid">
                <div class="info-item"><div class="info-label">Region</div><div class="info-value">${{unit.nrc_region}}</div></div>
                <div class="info-item"><div class="info-label">Units</div><div class="info-value">${{site.units.length}}</div></div>
                <div class="info-item"><div class="info-label">Capacity</div><div class="info-value">${{totalCap}} MWe</div></div>
                <div class="info-item"><div class="info-label">Avg CF</div><div class="info-value">${{cf != null ? cf.toFixed(1) + '%' : 'N/A'}}</div></div>
            </div>
            <div style="margin-top:0.75rem">${{unitsHtml}}</div>
        </div>
        <div class="popup-content" id="tab-news">
            ${{newsHtml}}
        </div>
        <div class="popup-content" id="tab-details">
            ${{site.units.map(u => `
                <div style="margin-bottom:0.75rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border-color)">
                    <div style="font-weight:600;margin-bottom:0.25rem">${{u.name.replace(site.name, '').replace(/^,\\s*/, '') || 'Unit 1'}}</div>
                    <div class="info-grid" style="margin-bottom:0.25rem">
                        <div class="info-item"><div class="info-label">Docket</div><div class="info-value">${{u.nrc_site_url ? `<a href="${{u.nrc_site_url}}" target="_blank" style="color:var(--tamu-maroon)">${{u.docket_number}}</a>` : u.docket_number}}</div></div>
                        <div class="info-item"><div class="info-label">License</div><div class="info-value">${{u.license_number || 'N/A'}}</div></div>
                        <div class="info-item"><div class="info-label">Capacity</div><div class="info-value">${{u.capacity_mwe || 'N/A'}} MWe</div></div>
                        <div class="info-item"><div class="info-label">Age</div><div class="info-value">${{u.current_age || 'N/A'}} yrs</div></div>
                    </div>
                </div>
            `).join('')}}
            <div style="font-size:0.75rem;color:var(--text-muted)">
                <div><strong>Operator:</strong> ${{unit.parent_company || 'N/A'}}</div>
                <div><strong>Containment:</strong> ${{unit.containment_type || 'N/A'}}</div>
            </div>
        </div>`;
    }}

    function getNewsHtml(units) {{
        // Collect news from ALL units at the site
        let allItems = [];
        for (const u of units) {{
            const docketNews = plantNews.by_docket?.[u.docket_number];
            if (docketNews && docketNews.items) {{
                // Add unit identifier to each item
                const unitLabel = u.name.match(/Unit\\s*\\d+|\\d+$/)?.[0] || '';
                docketNews.items.forEach(item => {{
                    allItems.push({{ ...item, unitLabel }});
                }});
            }}
        }}

        // Sort by date descending and take top 8
        allItems.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
        const items = allItems.slice(0, 8);

        if (!items.length) {{
            return '<p style="color:var(--text-muted);font-size:0.8rem">No recent regulatory news available.</p>';
        }}

        return items.map(item => `<div class="news-item">
            <div class="news-date">${{item.date || ''}} | ${{item.type || ''}}${{units.length > 1 && item.unitLabel ? ' | ' + item.unitLabel : ''}}</div>
            <div class="news-headline">${{item.headline}}</div>
            <a href="${{item.url}}" target="_blank" class="news-link">View Document</a>
        </div>`).join('');
    }}

    function switchTab(el, tabId) {{
        const popup = el.closest('.leaflet-popup-content');
        popup.querySelectorAll('.popup-tab').forEach(t => t.classList.remove('active'));
        popup.querySelectorAll('.popup-content').forEach(c => c.classList.remove('active'));
        el.classList.add('active');
        popup.querySelector('#tab-' + tabId).classList.add('active');
    }}

    function updateStats() {{
        document.getElementById('s-reactors').textContent = fleetStats.total_reactors || '--';
        document.getElementById('s-capacity').textContent = fleetStats.total_capacity_gwe || '--';
        document.getElementById('s-cf').textContent = (fleetStats.fleet_capacity_factor || '--') + '%';
        document.getElementById('s-pwr').textContent = fleetStats.pwr_count || '--';
        document.getElementById('s-bwr').textContent = fleetStats.bwr_count || '--';
        document.getElementById('update-date').textContent = fleetStats.data_as_of || '--';

        const sc = fleetStats.status_counts || {{}};
        document.getElementById('st-full').textContent = sc.full_power || 0;
        document.getElementById('st-reduced').textContent = sc.reduced_power || 0;
        document.getElementById('st-low').textContent = sc.low_power || 0;
        document.getElementById('st-offline').textContent = sc.offline || 0;
    }}

    function updateSidebar() {{
        const sorted = reactorData
            .filter(r => r.performance?.capacity_factor_365d != null)
            .sort((a,b) => b.performance.capacity_factor_365d - a.performance.capacity_factor_365d);

        const top5 = sorted.slice(0, 5);
        const bottom5 = sorted.slice(-5).reverse();

        document.getElementById('top-list').innerHTML = top5.map(r =>
            `<li class="performer-item" data-lat="${{r.coordinates?.latitude}}" data-lng="${{r.coordinates?.longitude}}">
                <span>${{getBaseName(r.name)}}</span>
                <span class="cf-high">${{r.performance.capacity_factor_365d.toFixed(1)}}%</span>
            </li>`
        ).join('');

        document.getElementById('bottom-list').innerHTML = bottom5.map(r =>
            `<li class="performer-item" data-lat="${{r.coordinates?.latitude}}" data-lng="${{r.coordinates?.longitude}}">
                <span>${{getBaseName(r.name)}}</span>
                <span class="cf-low">${{r.performance.capacity_factor_365d.toFixed(1)}}%</span>
            </li>`
        ).join('');
    }}

    function setupEvents() {{
        document.getElementById('dark-toggle').onclick = () => document.body.classList.toggle('dark-mode');

        document.getElementById('f-region').onchange = e => {{
            filters.region = e.target.value;
            updateMarkers();
        }};

        document.getElementById('f-type').onchange = e => {{
            filters.type = e.target.value;
            updateMarkers();
        }};

        document.getElementById('search').oninput = e => {{
            const q = e.target.value.toLowerCase();
            if (q.length < 2) return;
            const match = reactorData.find(r =>
                r.name.toLowerCase().includes(q) ||
                r.parent_company?.toLowerCase().includes(q)
            );
            if (match?.coordinates) {{
                map.setView([match.coordinates.latitude, match.coordinates.longitude], 8);
            }}
        }};

        document.querySelectorAll('.performer-item').forEach(item => {{
            item.onclick = () => {{
                const lat = parseFloat(item.dataset.lat);
                const lng = parseFloat(item.dataset.lng);
                if (lat && lng) {{
                    map.setView([lat, lng], 8);
                    markers.forEach(m => {{
                        const pos = m.getLatLng();
                        if (Math.abs(pos.lat - lat) < 0.01 && Math.abs(pos.lng - lng) < 0.01) m.openPopup();
                    }});
                }}
            }};
        }});
    }}

    document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', init) : init();
    </script>
</body>
</html>'''

    return html


def main():
    print("="*60)
    print("Dashboard Builder")
    print("="*60)

    html = build_html()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"Size: {file_size / 1024:.1f} KB")
    print("\nDashboard built successfully!")


if __name__ == "__main__":
    main()
