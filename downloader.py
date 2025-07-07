import os
import json
import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

# Configuration
PROZORRO_API_URL = "https://public.api.openprocurement.org/api/2.4/tenders"
TED_API_URL = "https://ted.europa.eu/api/v2.0/notices/search"
OUTPUT_DIR = "downloaded_tenders"
MAX_RESULTS = 50  # Maximum tenders to download per request
RATE_LIMIT_DELAY = 1.5  # Seconds between requests to respect API limits

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
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Build query parameters
    params = {
        "descending": 1,  # Newest first
        "limit": MAX_RESULTS,
        "offset": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    
    if keywords:
        params["q"] = " OR ".join(keywords)
    
    try:
        # Fetch tender list
        response = requests.get(PROZORRO_API_URL, params=params)
        response.raise_for_status()
        tenders = response.json()["data"]
        
        print(f"✅ Знайдено {len(tenders)} тендерів з ProZorro")
        
        # Download full tender details
        downloaded = []
        for tender in tenders:
            tender_id = tender["id"]
            try:
                # Fetch full tender data
                tender_url = f"{PROZORRO_API_URL}/{tender_id}"
                tender_response = requests.get(tender_url)
                tender_response.raise_for_status()
                tender_data = tender_response.json()["data"]
                
                # Save to file
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
                
                # Respect rate limit
                time.sleep(RATE_LIMIT_DELAY)
                
            except Exception as e:
                print(f"⚠️ Помилка при завантаженні тендеру {tender_id}: {str(e)}")
        
        print(f"💾 Успішно збережено {len(downloaded)} тендерів з ProZorro")
        return downloaded
        
    except Exception as e:
        print(f"❌ Критична помилка при роботі з API ProZorro: {str(e)}")
        return []

def download_ted_tenders(keywords=None, days_back=7, country="UA"):
    """
    Download tenders from TED API (European Union)
    Docs: https://ted.europa.eu/TED/misc/helpPage.do?name=apiHelp&locale=en
    """
    print("🔍 Пошук тендерів у системі TED...")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Build query payload (XML format required)
    query = f"""
    <QUERY>
        <SELECT>
            <FIELD>ND</FIELD>
            <FIELD>TI</FIELD>
            <FIELD>PD</FIELD>
            <FIELD>NC</FIELD>
            <FIELD>NU</FIELD>
            <FIELD>PR</FIELD>
            <FIELD>TD</FIELD>
            <FIELD>OJ</FIELD>
            <FIELD>HD</FIELD>
            <FIELD>CY</FIELD>
            <FIELD>AA</FIELD>
        </SELECT>
        <WHERE>
            <AND>
                <GT DATE="{start_date.strftime('%Y%m%d')}"/>
                <LT DATE="{end_date.strftime('%Y%m%d')}"/>
                <EQUAL>
                    <FIELD>TD</FIELD>
                    <VALUE>CONTRACT</VALUE>
                </EQUAL>
                <EQUAL>
                    <FIELD>TY</FIELD>
                    <VALUE>CN</VALUE>
                </EQUAL>
    """
    
    if country:
        query += f"""
                <EQUAL>
                    <FIELD>CY</FIELD>
                    <VALUE>{country}</VALUE>
                </EQUAL>
        """
    
    if keywords:
        keyword_query = " OR ".join([f'<CONTAINS><FIELD>TW</FIELD><VALUE>{kw}</VALUE></CONTAINS>' for kw in keywords])
        query += f"<OR>{keyword_query}</OR>"
    
    query += """
            </AND>
        </WHERE>
        <SORT>
            <DESCENDING>PD</DESCENDING>
        </SORT>
        <LIMIT>0,{max_results}</LIMIT>
    </QUERY>
    """.format(max_results=MAX_RESULTS)
    
    try:
        headers = {
            "Content-Type": "application/xml",
            "Accept": "application/json"
        }
        
        # Send request to TED API
        response = requests.post(TED_API_URL, data=query, headers=headers)
        response.raise_for_status()
        
        # Parse JSON response
        ted_data = response.json()
        
        if "error" in ted_data:
            print(f"❌ Помилка TED API: {ted_data['error']['message']}")
            return []
        
        notices = ted_data.get("results", [])
        print(f"✅ Знайдено {len(notices)} тендерів з TED")
        
        # Download full notices
        downloaded = []
        for notice in notices:
            try:
                notice_id = notice["ND"]
                notice_url = f"https://ted.europa.eu/api/v2.0/notices/{notice_id}"
                
                # Fetch full notice data
                notice_response = requests.get(notice_url)
                notice_response.raise_for_status()
                notice_data = notice_response.json()
                
                # Save to file
                filename = f"TED_{notice_id}.json"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(notice_data, f, ensure_ascii=False, indent=2)
                
                downloaded.append({
                    "id": notice_id,
                    "title": notice.get("TI", "Без назви"),
                    "date": notice.get("PD", ""),
                    "budget": notice.get("PR", 0),
                    "country": notice.get("CY", ""),
                    "file": filename
                })
                
                # Respect rate limit
                time.sleep(RATE_LIMIT_DELAY)
                
            except Exception as e:
                print(f"⚠️ Помилка при завантаженні тендеру {notice_id}: {str(e)}")
        
        print(f"💾 Успішно збережено {len(downloaded)} тендерів з TED")
        return downloaded
        
    except Exception as e:
        print(f"❌ Критична помилка при роботі з API TED: {str(e)}")
        return []

def main():
    # Initialize environment
    setup_environment()
    
    # Configuration parameters
    search_keywords = ["будівництво", "IT", "медичне обладнання"]
    days_to_search = 30
    ted_country = "UA"  # UA for Ukraine, or None for all countries
    
    # Download from ProZorro
    prozorro_tenders = download_prozorro_tenders(
        keywords=search_keywords,
        days_back=days_to_search
    )
    
    # Download from TED
    ted_tenders = download_ted_tenders(
        keywords=search_keywords,
        days_back=days_to_search,
        country=ted_country
    )
    
    # Create summary report
    summary = {
        "timestamp": datetime.now().isoformat(),
        "prozorro_count": len(prozorro_tenders),
        "ted_count": len(ted_tenders),
        "total_tenders": len(prozorro_tenders) + len(ted_tenders),
        "keywords": search_keywords,
        "date_range": f"Last {days_to_search} days"
    }
    
    # Save summary
    summary_file = os.path.join(OUTPUT_DIR, "download_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print("\n📊 Результати завантаження:")
    print(f"• Завантажено тендерів з ProZorro: {len(prozorro_tenders)}")
    print(f"• Завантажено тендерів з TED: {len(ted_tenders)}")
    print(f"• Загальна кількість: {len(prozorro_tenders) + len(ted_tenders)}")
    print(f"• Звіт збережено: {summary_file}")

if __name__ == "__main__":
    import time
    start_time = time.time()
    main()
    print(f"⏱️ Час виконання: {time.time() - start_time:.2f} секунд")