#!/usr/bin/env python3
"""
ADAMS Activity Fetcher for Nuclear Dashboard
Fetches recent regulatory documents from NRC ADAMS for each reactor.
Uses LLM to generate summaries of document activity.
"""

import requests
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configuration
BASE_DIR = "/home/dwatson/projects/plant_dashboard"
OUTPUT_DIR = os.path.join(BASE_DIR, "data")
REACTORS_JSON = os.path.join(OUTPUT_DIR, "reactors.json")
ADAMS_OUTPUT = os.path.join(OUTPUT_DIR, "adams_activity.json")

# LLM Configuration (from example_request.py)
API_URL = "http://47.218.246.93:1776/v1/chat/completions"
API_KEY = "sk-rNk4hHbQ0GZ6DIyYg3h5UQ"
SUMMARY_MODEL = "llama3.2-1b"

# ADAMS API Configuration
ADAMS_BASE_URL = "https://adams.nrc.gov/wba/services/search/advanced/nrc"
DOCS_PER_DOCKET = 5  # Number of recent documents to fetch per reactor
MAX_WORKERS = 5  # Concurrent requests


def search_docket(docket_number, max_results=10):
    """Search for documents by docket number"""
    lib_flag = "public-library"
    # Use 'starts' operator for exact docket match (ADAMS API requirement)
    filter_condition = f"!(DocketNumber,starts,'{quote(str(docket_number))}','')"
    sections = [
        f"filters:({lib_flag}:!t)",
        f"properties_search_all:!({filter_condition})"
    ]

    q_param = f"(mode:sections,sections:({','.join(sections)}))"
    params = {
        "q": q_param,
        "qn": "AdamsSearch",
        "tab": "advanced-search-pars",
        "start": 0,
        "rows": max_results,
        "s": "PublishDatePARS",  # Sort by publish date
        "so": "desc"             # Most recent first
    }

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (ADAMS API Client)'}
        response = requests.get(ADAMS_BASE_URL, params=params, headers=headers, timeout=20)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        results = []

        for res_elem in root.findall(".//result"):
            rec = {child.tag: child.text for child in res_elem}

            doc_metadata = {
                'title': rec.get('DocumentTitle', ''),
                'accession_number': rec.get('AccessionNumber', ''),
                'document_date': rec.get('DocumentDate', ''),
                'publish_date': rec.get('PublishDatePARS', ''),
                'document_type': rec.get('DocumentType', ''),
                'author_name': rec.get('AuthorName', ''),
                'author_affiliation': rec.get('AuthorAffiliation', ''),
                'docket_number': rec.get('DocketNumber', ''),
                'page_count': rec.get('EstimatedPageCount', '')
            }

            # Add document URL
            if doc_metadata['accession_number']:
                acc = doc_metadata['accession_number']
                if acc.startswith('ML'):
                    folder = acc[:6]
                    doc_metadata['url'] = f"https://www.nrc.gov/docs/{folder}/{acc}.pdf"

            results.append(doc_metadata)

        return results

    except Exception as e:
        print(f"  Error searching docket {docket_number}: {e}")
        return []


def is_plant_specific(docket_field, target_docket):
    """Check if document is plant-specific (tagged to 5 or fewer dockets)"""
    if not docket_field:
        return True  # No docket info, assume specific
    dockets = [d.strip() for d in str(docket_field).split(',')]
    # If tagged to more than 5 dockets, it's likely an industry-wide notice
    return len(dockets) <= 5

def categorize_document(doc_type, title):
    """Categorize document for activity tracking"""
    doc_type_lower = (doc_type or '').lower()
    title_lower = (title or '').lower()

    if 'ler' in doc_type_lower or 'licensee event report' in title_lower:
        return 'LER'
    elif 'inspection' in doc_type_lower or 'inspection' in title_lower:
        return 'Inspection'
    elif 'enforcement' in doc_type_lower or 'violation' in title_lower:
        return 'Enforcement'
    elif 'amendment' in doc_type_lower or 'license amendment' in title_lower:
        return 'License Amendment'
    elif 'correspondence' in doc_type_lower or 'letter' in doc_type_lower:
        return 'Correspondence'
    elif 'report' in doc_type_lower:
        return 'Report'
    else:
        return 'Other'


def generate_activity_summary(reactor_name, documents):
    """Use LLM to generate a brief summary of recent activity"""
    if not documents:
        return "No recent regulatory activity."

    # Build document list text
    doc_list = "\n".join([
        f"- {d['document_type']}: {d['title'][:100]}"
        for d in documents[:5]
    ])

    payload = {
        "model": SUMMARY_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a nuclear regulatory analyst. Provide brief, factual summaries."
            },
            {
                "role": "user",
                "content": f"""Summarize the recent NRC regulatory activity for {reactor_name} in 1-2 sentences based on these documents:

{doc_list}

Provide a brief summary focusing on any notable items (inspections, events, license actions). If routine, say so."""
            }
        ],
        "temperature": 0.3,
        "max_tokens": 100
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  LLM summary error: {e}")

    return "Recent regulatory activity on file."


def fetch_reactor_activity(reactor):
    """Fetch ADAMS activity for a single reactor"""
    name = reactor['name']
    docket = reactor['docket_number']

    if not docket:
        return None

    print(f"  Fetching: {name} ({docket})")

    # Fetch more docs than needed, then filter to plant-specific ones
    all_docs = search_docket(docket, max_results=DOCS_PER_DOCKET * 10)

    # Filter to plant-specific documents (not industry-wide notices)
    docs = [d for d in all_docs if is_plant_specific(d.get('docket_number', ''), docket)][:DOCS_PER_DOCKET]

    if not docs:
        return {
            'name': name,
            'docket': docket,
            'documents': [],
            'document_count': 0,
            'last_activity': None,
            'summary': "No recent documents found.",
            'categories': {}
        }

    # Categorize documents
    categories = {}
    for doc in docs:
        cat = categorize_document(doc['document_type'], doc['title'])
        doc['category'] = cat
        categories[cat] = categories.get(cat, 0) + 1

    # Get most recent date
    dates = [d['publish_date'] for d in docs if d.get('publish_date')]
    last_activity = max(dates) if dates else None

    # Generate summary (optional - can be slow)
    # summary = generate_activity_summary(name, docs)
    summary = f"{len(docs)} recent document(s) on file."

    return {
        'name': name,
        'docket': docket,
        'documents': docs,
        'document_count': len(docs),
        'last_activity': last_activity,
        'summary': summary,
        'categories': categories
    }


def main():
    print("="*60)
    print("ADAMS Activity Fetcher")
    print("="*60)

    # Load reactor data
    print("\nLoading reactor data...")
    with open(REACTORS_JSON, 'r') as f:
        reactors = json.load(f)

    print(f"  Found {len(reactors)} reactors")

    # Get unique dockets (avoid duplicates for multi-unit sites)
    unique_dockets = {}
    for r in reactors:
        docket = r['docket_number']
        if docket and docket not in unique_dockets:
            unique_dockets[docket] = r

    print(f"  {len(unique_dockets)} unique dockets to query")

    # Fetch activity for each reactor
    print("\nFetching ADAMS activity...")
    results = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_reactor_activity, r): r['docket_number']
            for r in unique_dockets.values()
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    results[result['docket']] = result
            except Exception as e:
                print(f"  Error: {e}")

    # Calculate fleet-wide activity summary
    total_docs = sum(r['document_count'] for r in results.values())
    active_reactors = sum(1 for r in results.values() if r['document_count'] > 0)

    # Count category totals
    all_categories = {}
    for r in results.values():
        for cat, count in r.get('categories', {}).items():
            all_categories[cat] = all_categories.get(cat, 0) + count

    output = {
        'fetched_at': datetime.now().isoformat(),
        'total_documents': total_docs,
        'reactors_with_activity': active_reactors,
        'category_totals': all_categories,
        'by_docket': results
    }

    # Save results
    print(f"\nSaving results to {ADAMS_OUTPUT}...")
    with open(ADAMS_OUTPUT, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n  Total documents found: {total_docs}")
    print(f"  Reactors with activity: {active_reactors}")
    print("  Categories:", dict(all_categories))

    print("\n" + "="*60)
    print("ADAMS activity fetch complete!")
    print("="*60)


if __name__ == "__main__":
    main()
