#!/usr/bin/env python3
"""
Nuclear Dashboard Data Processor
Processes reactor master data and capacity factor CSV into optimized JSON for browser consumption.

Data Sources:
- data/reactors_master.csv: Master reactor information (extracted from NRC data)
- nrc_reactor_status_unified_fixed.csv: Daily capacity factor data
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import re
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Configuration
BASE_DIR = "/home/dwatson/projects/plant_dashboard"
REACTORS_MASTER = os.path.join(BASE_DIR, "data", "reactors_master.csv")
CAPACITY_CSV = os.path.join(BASE_DIR, "nrc_reactor_status_unified_fixed.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "data")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_reactors_master():
    """Load reactor data from master CSV file"""
    print("Loading reactor master data...")
    df = pd.read_csv(REACTORS_MASTER)

    reactors = []
    for _, row in df.iterrows():
        # Determine license renewal status
        has_subsequent = pd.notna(row.get('subsequent_renewal')) and row.get('subsequent_renewal')
        has_renewed = pd.notna(row.get('license_renewed')) and row.get('license_renewed')

        if has_subsequent:
            license_status = 'subsequent_renewal'
            license_years = 80
        elif has_renewed:
            license_status = 'first_renewal'
            license_years = 60
        else:
            license_status = 'original'
            license_years = 40

        # Calculate age if we have commercial operation date
        current_age = None
        time_remaining = None
        pct_remaining = None

        commercial_op = row.get('commercial_operation')
        license_expires = row.get('license_expires')

        if pd.notna(commercial_op) and commercial_op:
            try:
                op_date = pd.to_datetime(commercial_op)
                current_age = (datetime.now() - op_date).days // 365
            except:
                pass

        if pd.notna(license_expires) and license_expires:
            try:
                exp_date = pd.to_datetime(license_expires)
                time_remaining = (exp_date - datetime.now()).days / 365
                if license_years > 0:
                    pct_remaining = (time_remaining / license_years) * 100
            except:
                pass

        # Build coordinates dict
        coords = None
        if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')):
            coords = {
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude'])
            }

        reactor = {
            'name': str(row.get('name', '')),
            'docket_number': str(row.get('docket_number', '')),
            'license_number': str(row.get('license_number', '')) if pd.notna(row.get('license_number')) else '',
            'location': str(row.get('location', '')) if pd.notna(row.get('location')) else '',
            'nrc_region': int(row.get('nrc_region')) if pd.notna(row.get('nrc_region')) else None,
            'reactor_type': str(row.get('reactor_type', '')) if pd.notna(row.get('reactor_type')) else '',
            'containment_type': str(row.get('containment_type', '')) if pd.notna(row.get('containment_type')) else '',
            'nsss_supplier': str(row.get('nsss_supplier', '')) if pd.notna(row.get('nsss_supplier')) else '',
            'architect_engineer': str(row.get('architect_engineer', '')) if pd.notna(row.get('architect_engineer')) else '',
            'constructor': str(row.get('constructor', '')) if pd.notna(row.get('constructor')) else '',
            'parent_company': str(row.get('parent_company', '')) if pd.notna(row.get('parent_company')) else '',
            'licensee': str(row.get('licensee', '')) if pd.notna(row.get('licensee')) else '',
            'parent_website': str(row.get('parent_website', '')) if pd.notna(row.get('parent_website')) else '',
            'licensed_mwt': float(row.get('licensed_mwt')) if pd.notna(row.get('licensed_mwt')) else None,
            'capacity_mwe': int(row.get('capacity_mwe')) if pd.notna(row.get('capacity_mwe')) else None,
            'dates': {
                'construction_permit': str(row.get('construction_permit', '')) if pd.notna(row.get('construction_permit')) else None,
                'operating_license': str(row.get('operating_license', '')) if pd.notna(row.get('operating_license')) else None,
                'commercial_operation': str(row.get('commercial_operation', '')) if pd.notna(row.get('commercial_operation')) else None,
                'license_renewed': str(row.get('license_renewed', '')) if pd.notna(row.get('license_renewed')) else None,
                'license_expires': str(row.get('license_expires', '')) if pd.notna(row.get('license_expires')) else None,
                'subsequent_renewal': str(row.get('subsequent_renewal', '')) if pd.notna(row.get('subsequent_renewal')) else None,
            },
            'license_status': license_status,
            'license_years': license_years,
            'current_age': current_age,
            'time_remaining': round(time_remaining, 1) if time_remaining else None,
            'pct_license_remaining': round(pct_remaining, 1) if pct_remaining else None,
            'coordinates': coords,
            'nrc_site_url': str(row.get('nrc_site_url', '')) if pd.notna(row.get('nrc_site_url')) else None,
            'historical_capacity_factors': {}  # Will be populated from capacity CSV if needed
        }

        reactors.append(reactor)

    print(f"  Loaded {len(reactors)} reactors from master CSV")
    return reactors


def get_plant_base_name(full_name):
    """Extract plant base name from full unit name"""
    # Remove unit numbers like ", Unit 1" or " 1" or " Unit 1"
    name = re.sub(r',?\s*(Unit\s*)?\d+$', '', full_name, flags=re.IGNORECASE)
    return name.strip()


def process_capacity_factors():
    """Process capacity factor CSV into optimized summaries"""
    print("Processing capacity factor CSV...")

    # Read CSV in chunks to handle large file
    chunks = []
    for chunk in pd.read_csv(CAPACITY_CSV, chunksize=100000):
        chunks.append(chunk)

    df = pd.concat(chunks, ignore_index=True)
    print(f"  Loaded {len(df)} records")

    # Convert Date column
    df['Date'] = pd.to_datetime(df['Date'])

    # Get the most recent date in the data
    max_date = df['Date'].max()
    print(f"  Data through: {max_date.strftime('%Y-%m-%d')}")

    # Get unique unit names
    units = df['Unit'].unique()
    print(f"  Processing {len(units)} units...")

    reactor_metrics = {}

    for unit_name in units:
        unit_df = df[df['Unit'] == unit_name].copy()
        unit_df = unit_df.sort_values('Date')

        # Current power (most recent)
        latest = unit_df[unit_df['Date'] == max_date]
        current_power = latest['Power'].values[0] if len(latest) > 0 else None

        # Determine status
        if current_power is None:
            status = 'offline'
        elif current_power >= 95:
            status = 'full_power'
        elif current_power >= 50:
            status = 'reduced_power'
        elif current_power > 0:
            status = 'low_power'
        else:
            status = 'offline'

        # Calculate capacity factors for different periods
        cf_30 = unit_df[unit_df['Date'] >= max_date - timedelta(days=30)]['Power'].mean()
        cf_90 = unit_df[unit_df['Date'] >= max_date - timedelta(days=90)]['Power'].mean()
        cf_365 = unit_df[unit_df['Date'] >= max_date - timedelta(days=365)]['Power'].mean()
        cf_lifetime = unit_df['Power'].mean()

        # Round values
        cf_30 = round(cf_30, 1) if pd.notna(cf_30) else None
        cf_90 = round(cf_90, 1) if pd.notna(cf_90) else None
        cf_365 = round(cf_365, 1) if pd.notna(cf_365) else None
        cf_lifetime = round(cf_lifetime, 1) if pd.notna(cf_lifetime) else None

        # Outage tracking (last year)
        last_year_df = unit_df[unit_df['Date'] >= max_date - timedelta(days=365)].copy()
        last_year_df['is_outage'] = last_year_df['Power'] < 5

        # Count outage starts
        outage_starts = (last_year_df['is_outage'] & ~last_year_df['is_outage'].shift(1).fillna(False)).sum()
        outage_days = last_year_df['is_outage'].sum()

        # Days since last outage
        recent_outages = last_year_df[last_year_df['is_outage']]
        if len(recent_outages) > 0:
            days_since_outage = (max_date - recent_outages['Date'].max()).days
        else:
            days_since_outage = 365

        # Longest continuous run at high power
        unit_df['high_power'] = unit_df['Power'] >= 95
        unit_df['run_group'] = (~unit_df['high_power']).cumsum()
        if unit_df['high_power'].any():
            longest_run = unit_df[unit_df['high_power']].groupby('run_group').size().max()
        else:
            longest_run = 0

        # Monthly averages for sparkline (last 12 months)
        last_year_df = unit_df[unit_df['Date'] >= max_date - timedelta(days=365)]
        monthly = last_year_df.set_index('Date').resample('ME')['Power'].mean()
        monthly_data = [round(v, 1) for v in monthly.values if pd.notna(v)]

        # Calculate trend
        prev_90 = unit_df[(unit_df['Date'] >= max_date - timedelta(days=180)) &
                          (unit_df['Date'] < max_date - timedelta(days=90))]
        if len(prev_90) > 0 and cf_90 is not None:
            prev_cf = prev_90['Power'].mean()
            if cf_90 > prev_cf + 2:
                trend = 'up'
            elif cf_90 < prev_cf - 2:
                trend = 'down'
            else:
                trend = 'stable'
        else:
            trend = 'stable'

        reactor_metrics[unit_name] = {
            'current_power': current_power,
            'status': status,
            'capacity_factor_30d': cf_30,
            'capacity_factor_90d': cf_90,
            'capacity_factor_365d': cf_365,
            'capacity_factor_lifetime': cf_lifetime,
            'trend': trend,
            'outages_last_year': int(outage_starts),
            'outage_days_last_year': int(outage_days),
            'days_since_outage': int(days_since_outage),
            'longest_run_days': int(longest_run),
            'monthly_cf': monthly_data,
            'data_as_of': max_date.strftime('%Y-%m-%d')
        }

    print(f"  Calculated metrics for {len(reactor_metrics)} reactors")
    return reactor_metrics


def calculate_fleet_statistics(reactors, cf_metrics):
    """Calculate fleet-wide statistics"""
    print("Calculating fleet statistics...")

    # Total capacity
    total_capacity_mwe = sum(r.get('capacity_mwe', 0) or 0 for r in reactors)
    total_capacity_gwe = round(total_capacity_mwe / 1000, 1)

    # Reactor counts by type
    pwr_count = sum(1 for r in reactors if r['reactor_type'] == 'PWR')
    bwr_count = sum(1 for r in reactors if r['reactor_type'] == 'BWR')

    # Reactor counts by region
    by_region = defaultdict(int)
    for r in reactors:
        if r['nrc_region']:
            by_region[r['nrc_region']] += 1

    # Average age
    ages = [r['current_age'] for r in reactors if r.get('current_age')]
    avg_age = round(sum(ages) / len(ages), 1) if ages else 0

    # License status counts
    original_license = sum(1 for r in reactors if r['license_status'] == 'original')
    first_renewal = sum(1 for r in reactors if r['license_status'] == 'first_renewal')
    subsequent_renewal = sum(1 for r in reactors if r['license_status'] == 'subsequent_renewal')

    # Fleet capacity factor
    cf_values = [m['capacity_factor_90d'] for m in cf_metrics.values() if m.get('capacity_factor_90d')]
    fleet_cf = round(sum(cf_values) / len(cf_values), 1) if cf_values else 0

    # Status counts
    status_counts = defaultdict(int)
    for m in cf_metrics.values():
        status_counts[m['status']] += 1

    # Count unique plant sites
    plant_sites = set()
    for r in reactors:
        base_name = get_plant_base_name(r['name'])
        plant_sites.add(base_name)

    stats = {
        'total_reactors': len(reactors),
        'total_sites': len(plant_sites),
        'total_capacity_mwe': total_capacity_mwe,
        'total_capacity_gwe': total_capacity_gwe,
        'pwr_count': pwr_count,
        'bwr_count': bwr_count,
        'by_region': dict(by_region),
        'average_age': avg_age,
        'license_status': {
            'original': original_license,
            'first_renewal': first_renewal,
            'subsequent_renewal': subsequent_renewal
        },
        'fleet_capacity_factor': fleet_cf,
        'status_counts': dict(status_counts),
        'data_as_of': datetime.now().strftime('%Y-%m-%d')
    }

    print(f"  Total reactors: {stats['total_reactors']}")
    print(f"  Total capacity: {stats['total_capacity_gwe']} GWe")
    print(f"  Fleet CF: {stats['fleet_capacity_factor']}%")

    return stats


def create_name_mapping():
    """Create mapping from master names to CSV names"""
    return {
        # Master name -> CSV name
        "Callaway Plant": "Callaway 1",
        "Cooper Nuclear Station": "Cooper 1",
        "Davis-Besse Nuclear Power Station, Unit 1": "Davis-Besse",
        "Donald C. Cook Nuclear Plant, Unit 1": "D.C. Cook 1",
        "Donald C. Cook Nuclear Plant, Unit 2": "D.C. Cook 2",
        "James A. FitzPatrick Nuclear Power Plant": "Fitzpatrick 1",
        "R.E. Ginna Nuclear Power Plant": "Ginna 1",
        "St. Lucie Plant, Unit 1": "St. Lucie 1",
        "St. Lucie Plant, Unit 2": "St. Lucie 2",
        "Shearon Harris Nuclear Power Plant, Unit 1": "Harris 1",
        "Edwin I. Hatch Nuclear Plant, Unit 1": "Hatch 1",
        "Edwin I. Hatch Nuclear Plant, Unit 2": "Hatch 2",
        "Joseph M. Farley Nuclear Plant, Unit 1": "Farley 1",
        "Joseph M. Farley Nuclear Plant, Unit 2": "Farley 2",
        "H.B. Robinson Steam Electric Plant, Unit 2": "Robinson 2",
        "H. B. Robinson Steam Electric Plant, Unit 2": "Robinson 2",
        "V.C. Summer Nuclear Station, Unit 1": "Summer 1",
        "Virgil C. Summer Nuclear Station, Unit 1": "Summer 1",
        "Palisades Nuclear Plant": "Palisades 1",
    }


def normalize_name_for_matching(name):
    """Normalize reactor name for matching"""
    # Remove common suffixes
    name = re.sub(r'\s*(Nuclear\s*)?(Power\s*)?(Plant|Station|Generating Station).*$', '', name, flags=re.IGNORECASE)
    # Remove "Unit" prefix before number
    name = re.sub(r',?\s*Unit\s*', ' ', name)
    # Handle "One" -> "1", etc
    name = re.sub(r'\bOne\b', '1', name)
    name = re.sub(r'\bTwo\b', '2', name)
    name = re.sub(r'\bThree\b', '3', name)
    # Normalize whitespace
    name = ' '.join(name.split())
    return name.strip()


def merge_data(reactors, cf_metrics):
    """Merge reactor data with capacity factor metrics"""
    print("Merging reactor and capacity factor data...")

    name_mapping = create_name_mapping()

    # Create normalized lookup for CF metrics
    cf_normalized = {}
    for cf_name in cf_metrics.keys():
        normalized = normalize_name_for_matching(cf_name).lower()
        cf_normalized[normalized] = cf_name

    matched = 0
    unmatched = 0

    for reactor in reactors:
        name = reactor['name']

        # Try direct mapping first
        if name in name_mapping:
            mapped_name = name_mapping[name]
            if mapped_name in cf_metrics:
                reactor['performance'] = cf_metrics[mapped_name]
                matched += 1
                continue

        # Try exact match
        if name in cf_metrics:
            reactor['performance'] = cf_metrics[name]
            matched += 1
            continue

        # Try normalized matching
        normalized = normalize_name_for_matching(name).lower()
        if normalized in cf_normalized:
            reactor['performance'] = cf_metrics[cf_normalized[normalized]]
            matched += 1
            continue

        # Try partial matching with unit number
        reactor_base = get_plant_base_name(name).lower()
        reactor_unit = re.search(r'(\d+)$', name)
        unit_num = reactor_unit.group(1) if reactor_unit else None

        found = False
        for cf_name in cf_metrics.keys():
            cf_base = get_plant_base_name(cf_name).lower()
            cf_unit = re.search(r'(\d+)$', cf_name)
            cf_unit_num = cf_unit.group(1) if cf_unit else None

            if (reactor_base in cf_base or cf_base in reactor_base or
                any(word in cf_base for word in reactor_base.split() if len(word) > 4)):
                if unit_num == cf_unit_num or (unit_num is None and cf_unit_num is None):
                    reactor['performance'] = cf_metrics[cf_name]
                    matched += 1
                    found = True
                    break

        if not found:
            print(f"  Warning: No performance data for {name}")
            reactor['performance'] = None
            unmatched += 1

    print(f"  Matched: {matched}, Unmatched: {unmatched}")
    return reactors


def main():
    print("="*60)
    print("Nuclear Dashboard Data Processor")
    print("="*60)

    # Load reactor data from master CSV
    reactors = load_reactors_master()

    # Process capacity factors
    cf_metrics = process_capacity_factors()

    # Merge data
    reactors = merge_data(reactors, cf_metrics)

    # Calculate fleet statistics
    fleet_stats = calculate_fleet_statistics(reactors, cf_metrics)

    # Save outputs
    print("\nSaving output files...")

    # Save reactor data
    with open(os.path.join(OUTPUT_DIR, 'reactors.json'), 'w') as f:
        json.dump(reactors, f, indent=2, cls=NumpyEncoder)
    print(f"  Saved reactors.json ({len(reactors)} reactors)")

    # Save capacity factor summary
    with open(os.path.join(OUTPUT_DIR, 'capacity_factors.json'), 'w') as f:
        json.dump(cf_metrics, f, indent=2, cls=NumpyEncoder)
    print(f"  Saved capacity_factors.json ({len(cf_metrics)} units)")

    # Save fleet statistics
    with open(os.path.join(OUTPUT_DIR, 'fleet_stats.json'), 'w') as f:
        json.dump(fleet_stats, f, indent=2, cls=NumpyEncoder)
    print(f"  Saved fleet_stats.json")

    print("\n" + "="*60)
    print("Data processing complete!")
    print("="*60)


if __name__ == "__main__":
    main()
