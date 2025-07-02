import requests
import os
import time

output_dir = "./tenders"

headers = {"User-Agent": "Mozilla/5.0"}
year = 2025
start = 36570
end = 520000
limit = 50
downloaded = 0

for number in range(start, end):
    tender_number = f"{number}-{year}"
    pdf_url = f"https://www.find-tender.service.gov.uk/Notice/0{tender_number}/pdf"

    try:
        response = requests.get(pdf_url, headers=headers)
        if response.status_code == 200 and response.headers["Content-Type"] == "application/pdf":
            print(f"[{downloaded+1}] Downloading {tender_number}...")
            with open(f"{output_dir}/{tender_number}.pdf", "wb") as f:
                f.write(response.content)
            downloaded += 1

            if downloaded >= limit:
                print("✅ Done")
                break

        else:
            print(f"❌ {tender_number} not found.")
        
        time.sleep(0.2)

    except Exception as e:
        print(f"⚠️ Error with {tender_number}: {e}")
