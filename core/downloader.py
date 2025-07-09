import os
import json
import time
import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

# Configuration
PROZORRO_API_URL = "https://public.api.openprocurement.org/api/2.4/tenders"
OUTPUT_DIR = "../tenders"
MAX_RESULTS = 3
RATE_LIMIT_DELAY = 1.5

def setup_environment():
    """Create output directory if it doesn't exist"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Output directory created: {OUTPUT_DIR}")
    
def download_prozorro_tenders(topic="Construction", total_to_download=10, days_back=7):
    """
    Download tenders from ProZorro API based on tender topic (using keywords.json)
    """
    print(f"🔍 Downloading tenders for topic: {topic}")

    # Load topic keywords
    keywords_path = "../data/keywords.json"
    if not os.path.exists(keywords_path):
        raise FileNotFoundError("❌ keywords.json not found!")

    with open(keywords_path, "r", encoding="utf-8") as f:
        topic_keywords = json.load(f).get(topic, [])
    
    if not topic_keywords:
        raise ValueError(f"❌ No keywords found for topic '{topic}' in keywords.json")

    setup_environment()
    
    downloaded = []
    offset_time = datetime.now()
    checked = 0

    while len(downloaded) < total_to_download and checked < 500:
        params = {
            "descending": 1,
            "limit": 100,
            "offset": offset_time.strftime("%Y-%m-%dT%H:%M:%S")
        }

        try:
            response = requests.get(PROZORRO_API_URL, params=params)
            response.raise_for_status()
            tenders = response.json().get("data", [])
            if not tenders:
                print("🚫 No more tenders found.")
                break

            for tender in tenders:
                tender_id = tender["id"]
                try:
                    tender_url = f"{PROZORRO_API_URL}/{tender_id}"
                    tender_response = requests.get(tender_url)
                    tender_response.raise_for_status()
                    tender_data = tender_response.json()["data"]

                    title = tender_data.get("title", "").lower()
                    description = tender_data.get("description", "").lower()

                    # Check if any keyword matches
                    if any(kw.lower() in title or kw.lower() in description for kw in topic_keywords):
                        filename = f"ProZorro_{tender_id}.json"
                        filepath = os.path.join(OUTPUT_DIR, filename)

                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(tender_data, f, ensure_ascii=False, indent=2)

                        downloaded.append({
                            "id": tender_id,
                            "title": tender_data.get("title", "Без назви"),
                            "date": tender_data.get("dateModified", ""),
                            "budget": tender_data.get("value", {}).get("amount", 0),
                            "file": filename
                        })
                        print(f"✅ Saved: {filename}")

                        if len(downloaded) >= total_to_download:
                            break

                    checked += 1
                    time.sleep(RATE_LIMIT_DELAY)

                except Exception as e:
                    print(f"⚠️ Error for {tender_id}: {e}")
                    continue

            # Update offset to last tender timestamp
            offset_time -= timedelta(minutes=10)

        except Exception as e:
            print(f"❌ API error: {e}")
            break

    print(f"\n💾 Total downloaded tenders: {len(downloaded)} for topic: {topic}")
    return downloaded