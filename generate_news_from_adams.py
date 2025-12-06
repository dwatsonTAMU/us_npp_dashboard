#!/usr/bin/env python3
"""
Generate news headlines from existing ADAMS data using LLM.
Faster than fetching fresh - uses cached ADAMS activity.
"""

import json
import os
import requests
import time
import re
from datetime import datetime

BASE_DIR = "/home/dwatson/projects/plant_dashboard"
DATA_DIR = os.path.join(BASE_DIR, "data")
ADAMS_SLIM = os.path.join(DATA_DIR, "adams_activity_slim.json")
NEWS_JSON = os.path.join(DATA_DIR, "plant_news.json")

# LLM Configuration
API_URL = "http://47.218.246.93:1776/v1/chat/completions"
API_KEY = "sk-rNk4hHbQ0GZ6DIyYg3h5UQ"
HEADLINE_MODEL = "llama3.2-1b"  # Faster model


def generate_headline(title, doc_type):
    """Generate a concise news headline using LLM."""
    title = title.strip()
    if len(title) < 30:
        return title

    payload = {
        "model": HEADLINE_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a headline writer. Create ONE concise news headline (10 words max) for NRC documents. Output ONLY the headline, no explanation."
            },
            {
                "role": "user",
                "content": f"Write a short headline for: {title[:200]}"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 30
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        if response.status_code == 200:
            data = response.json()
            headline = data["choices"][0]["message"]["content"].strip()
            # Clean up
            headline = headline.strip('"\'')
            headline = re.sub(r'^(Here is|Here\'s|Headline:)\s*', '', headline, flags=re.I)
            if len(headline) > 80:
                headline = headline[:77] + "..."
            return headline
    except Exception as e:
        pass

    # Fallback: truncate title
    if len(title) > 60:
        return title[:57] + "..."
    return title


def main():
    print("="*60)
    print("Generate News Headlines from ADAMS Data")
    print("="*60)

    # Load ADAMS data
    print("\nLoading ADAMS data...")
    with open(ADAMS_SLIM, 'r') as f:
        adams = json.load(f)

    by_docket = adams.get('by_docket', {})
    print(f"  Found {len(by_docket)} dockets")

    # Generate headlines for each document
    print("\nGenerating headlines...")
    output = {
        'updated_at': datetime.now().isoformat(),
        'by_docket': {}
    }

    total_docs = 0
    processed = 0

    for i, (docket, info) in enumerate(by_docket.items(), 1):
        docs = info.get('documents', [])
        if not docs:
            continue

        print(f"\n[{i}/{len(by_docket)}] {info.get('name', docket)}")

        items = []
        for doc in docs[:3]:  # Max 3 docs per docket
            title = doc.get('title', '')
            doc_type = doc.get('type', '')

            # Generate headline
            headline = generate_headline(title, doc_type)
            print(f"  -> {headline[:50]}...")

            items.append({
                'date': doc.get('date', ''),
                'headline': headline,
                'title': title[:100],
                'type': doc.get('category', doc_type),
                'accession': doc.get('accession', ''),
                'url': doc.get('url', '')
            })

            total_docs += 1
            time.sleep(0.3)  # Rate limit

        output['by_docket'][docket] = {
            'plant_name': info.get('name', ''),
            'items': items
        }
        processed += 1

    # Save output
    print(f"\n\nSaving {total_docs} headlines for {processed} dockets...")
    with open(NEWS_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"Saved to {NEWS_JSON}")
    print("\n" + "="*60)
    print("Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
