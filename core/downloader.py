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
MAX_RESULTS = 10
RATE_LIMIT_DELAY = 1.5

def setup_environment():
    """Create output directory if it doesn't exist"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Output directory created: {OUTPUT_DIR}")

def download_prozorro_tenders(keywords=None, days_back=7, save_full=False):
    """
    Download tenders from ProZorro API (Ukraine)
    Docs: https://prozorro-api-docs.readthedocs.io/uk/latest/
    """
    print("🔍 Пошук тендерів у системі ProZorro...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    params = {
        "descending": 1, 
        "limit": MAX_RESULTS,
        "offset": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    
    if keywords:
        params["q"] = " OR ".join(keywords)
    
    try:
        response = requests.get(PROZORRO_API_URL, params=params)
        response.raise_for_status()
        tenders = response.json()["data"]
        
        print(f"✅ Знайдено {len(tenders)} тендерів з ProZorro")
        
        downloaded = []
        for tender in tenders:
            tender_id = tender["id"]
            try:
                tender_url = f"{PROZORRO_API_URL}/{tender_id}"
                tender_response = requests.get(tender_url)
                tender_response.raise_for_status()
                tender_data = tender_response.json()["data"]
                
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
                
                time.sleep(RATE_LIMIT_DELAY)
                
            except Exception as e:
                print(f"⚠️ Помилка при завантаженні тендеру {tender_id}: {str(e)}")
        
        print(f"💾 Успішно збережено {len(downloaded)} тендерів з ProZorro")
        return downloaded
        
    except Exception as e:
        print(f"❌ Критична помилка при роботі з API ProZorro: {str(e)}")
        return []

def main():
    setup_environment()
    
    search_keywords = ["будівництво", "IT", "медичне обладнання"]
    days_to_search = 30
    
    prozorro_tenders = download_prozorro_tenders(
        keywords=search_keywords,
        days_back=days_to_search
    )
    
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "prozorro_count": len(prozorro_tenders),
        "total_tenders": len(prozorro_tenders),
        "keywords": search_keywords,
        "date_range": f"Last {days_to_search} days"
    }
    
    summary_file = os.path.join(OUTPUT_DIR, "download_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print("\n📊 Результати завантаження:")
    print(f"• Завантажено тендерів з ProZorro: {len(prozorro_tenders)}")
    print(f"• Звіт збережено: {summary_file}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"⏱️ Час виконання: {time.time() - start_time:.2f} секунд")