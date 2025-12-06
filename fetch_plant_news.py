#!/usr/bin/env python3
"""
Plant News Fetcher - Fetches ADAMS documents and generates LLM headlines for each reactor.
Stores news in a persistent CSV file for display in the dashboard.
"""

import requests
import json
import csv
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re

# Configuration
BASE_DIR = "/home/dwatson/projects/plant_dashboard"
DATA_DIR = os.path.join(BASE_DIR, "data")
REACTORS_JSON = os.path.join(DATA_DIR, "reactors.json")
NEWS_CSV = os.path.join(DATA_DIR, "plant_news.csv")
NEWS_JSON = os.path.join(DATA_DIR, "plant_news.json")

# LLM Configuration
API_URL = "http://47.218.246.93:1776/v1/chat/completions"
API_KEY = "sk-rNk4hHbQ0GZ6DIyYg3h5UQ"
HEADLINE_MODEL = "gemma2-27b"

# ADAMS API
ADAMS_BASE_URL = "https://adams.nrc.gov/wba/services/search/advanced/nrc"
DOCS_PER_DOCKET = 5
MAX_WORKERS = 3  # Limit concurrent LLM requests

os.makedirs(DATA_DIR, exist_ok=True)


def load_existing_news():
    """Load existing news items from CSV to avoid re-processing."""
    existing = {}
    if os.path.exists(NEWS_CSV):
        with open(NEWS_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get('accession_number', '')
                if key:
                    existing[key] = row
    return existing


def save_news_csv(news_items):
    """Save news items to CSV."""
    if not news_items:
        return

    fieldnames = ['docket', 'plant_name', 'accession_number', 'document_date',
                  'document_type', 'title', 'headline', 'url', 'fetched_at']

    with open(NEWS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in news_items:
            writer.writerow(item)

    print(f"Saved {len(news_items)} news items to {NEWS_CSV}")


def save_news_json(news_items):
    """Save news items to JSON for embedding in HTML."""
    # Group by docket
    by_docket = {}
    for item in news_items:
        docket = item['docket']
        if docket not in by_docket:
            by_docket[docket] = {
                'plant_name': item['plant_name'],
                'items': []
            }
        by_docket[docket]['items'].append({
            'date': item['document_date'],
            'headline': item['headline'],
            'title': item['title'][:100],
            'type': item['document_type'],
            'accession': item['accession_number'],
            'url': item['url']
        })

    # Sort items by date within each docket
    for docket in by_docket:
        by_docket[docket]['items'].sort(
            key=lambda x: x.get('date', ''),
            reverse=True
        )

    output = {
        'updated_at': datetime.now().isoformat(),
        'by_docket': by_docket
    }

    with open(NEWS_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"Saved news JSON to {NEWS_JSON}")


def search_docket(docket_number, max_results=10):
    """Search for documents by docket number."""
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

            accession = rec.get('AccessionNumber', '')
            if not accession or not accession.startswith('ML'):
                continue

            folder = accession[:6]
            url = f"https://www.nrc.gov/docs/{folder}/{accession}.pdf"

            results.append({
                'title': rec.get('DocumentTitle', ''),
                'accession_number': accession,
                'document_date': rec.get('DocumentDate', ''),
                'publish_date': rec.get('PublishDatePARS', ''),
                'document_type': rec.get('DocumentType', ''),
                'url': url
            })

        return results

    except Exception as e:
        print(f"  Error searching docket {docket_number}: {e}")
        return []


def generate_headline(title, doc_type):
    """Generate a concise news headline using LLM."""
    # Clean up title
    title = title.strip()
    if len(title) < 20:
        return title  # Too short to summarize

    payload = {
        "model": HEADLINE_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You create concise news headlines (max 15 words) for NRC nuclear regulatory documents. Be factual and informative. Output only the headline, no quotes or explanation."
            },
            {
                "role": "user",
                "content": f"Create a brief news headline for this NRC document:\nType: {doc_type}\nTitle: {title}"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 50
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=60)
        if response.status_code == 200:
            data = response.json()
            headline = data["choices"][0]["message"]["content"].strip()
            # Clean up headline
            headline = headline.strip('"\'')
            headline = re.sub(r'^(Here is|Here\'s|Headline:)\s*', '', headline, flags=re.I)
            if len(headline) > 100:
                headline = headline[:97] + "..."
            return headline
    except Exception as e:
        print(f"    LLM error: {e}")

    # Fallback: truncate title
    if len(title) > 80:
        return title[:77] + "..."
    return title


def process_reactor(reactor, existing_news):
    """Process a single reactor - fetch docs and generate headlines."""
    name = reactor['name']
    docket = reactor['docket_number']

    if not docket:
        return []

    print(f"  Processing: {name} ({docket})")

    docs = search_docket(docket, max_results=DOCS_PER_DOCKET)
    if not docs:
        return []

    news_items = []

    for doc in docs:
        accession = doc['accession_number']

        # Check if we already have a headline for this document
        if accession in existing_news:
            item = existing_news[accession]
            news_items.append(item)
            continue

        # Generate headline
        headline = generate_headline(doc['title'], doc['document_type'])

        news_items.append({
            'docket': docket,
            'plant_name': name,
            'accession_number': accession,
            'document_date': doc['document_date'],
            'document_type': doc['document_type'][:50] if doc['document_type'] else '',
            'title': doc['title'],
            'headline': headline,
            'url': doc['url'],
            'fetched_at': datetime.now().isoformat()
        })

        print(f"    + {headline[:60]}...")
        time.sleep(0.5)  # Rate limit LLM requests

    return news_items


def main():
    print("="*60)
    print("Plant News Fetcher")
    print("="*60)

    # Load reactor data
    print("\nLoading reactor data...")
    with open(REACTORS_JSON, 'r') as f:
        reactors = json.load(f)
    print(f"  Found {len(reactors)} reactors")

    # Load existing news
    existing_news = load_existing_news()
    print(f"  Found {len(existing_news)} existing news items")

    # Get unique dockets
    unique_reactors = {}
    for r in reactors:
        docket = r['docket_number']
        if docket and docket not in unique_reactors:
            unique_reactors[docket] = r

    print(f"  {len(unique_reactors)} unique dockets to process")

    # Process reactors
    print("\nFetching news and generating headlines...")
    all_news = []

    for i, reactor in enumerate(unique_reactors.values(), 1):
        print(f"\n[{i}/{len(unique_reactors)}]", end="")
        news = process_reactor(reactor, existing_news)
        all_news.extend(news)

    # Save results
    print(f"\n\nSaving {len(all_news)} total news items...")
    save_news_csv(all_news)
    save_news_json(all_news)

    print("\n" + "="*60)
    print("News fetch complete!")
    print("="*60)


if __name__ == "__main__":
    main()
