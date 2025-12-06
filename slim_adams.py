#!/usr/bin/env python3
"""Slim down ADAMS activity data to just essential info for the dashboard"""
import json

INPUT = "data/adams_activity.json"
OUTPUT = "data/adams_activity_slim.json"

with open(INPUT, 'r') as f:
    data = json.load(f)

# Keep only 3 most recent documents per docket
slim_data = {
    'fetched_at': data['fetched_at'],
    'total_documents': 0,
    'category_totals': data['category_totals'],
    'by_docket': {}
}

for docket, info in data['by_docket'].items():
    # Sort docs by publish_date (most recent first) and keep top 3
    docs = sorted(
        info['documents'],
        key=lambda d: d.get('publish_date', ''),
        reverse=True
    )[:3]

    # Slim down document info
    slim_docs = [{
        'title': d['title'][:150],  # Truncate long titles
        'accession': d['accession_number'],
        'date': d['document_date'],
        'type': d['document_type'][:50] if d['document_type'] else '',
        'category': d['category'],
        'url': d.get('url', '')
    } for d in docs]

    slim_data['by_docket'][docket] = {
        'name': info['name'],
        'last_activity': info['last_activity'],
        'documents': slim_docs,
        'categories': info['categories']
    }
    slim_data['total_documents'] += len(slim_docs)

with open(OUTPUT, 'w') as f:
    json.dump(slim_data, f)

print(f"Slimmed from {INPUT} to {OUTPUT}")
print(f"Total docs: {slim_data['total_documents']}")
