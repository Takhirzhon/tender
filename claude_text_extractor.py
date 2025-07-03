import os
import json
import time
import anthropic
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(
    api_key=os.getenv("CLAUDE_API_KEY")
)

TEXT_DIR = "tenders/text"
OUTPUT_CSV = "tenders/claude_extracted.csv"

COLUMNS = ["title", "issuer", "deadline", "budget", "location", "project_type", "filename"]
data = []

def ask_claude(text):
    prompt = f"""
Extract the following fields from the tender text below:
1. Title or Project Name
2. Issuer or Client
3. Submission Deadline
4. Estimated Budget
5. Location (City, Region, or Country)
6. Project Type or Scope of Work

Return the result strictly in the following JSON format:
{{
  "title": "...",
  "issuer": "...",
  "deadline": "...",
  "budget": "...",
  "location": "...",
  "project_type": "..."
}}

Tender Text:
\"\"\"
{text}
\"\"\"
"""
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        temperature=0.0,
        system="You are a helpful assistant that extracts structured information from public procurement tender documents.",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text  # type: ignore

for i, filename in enumerate(os.listdir(TEXT_DIR)):
    if not filename.endswith(".txt") or i >= 20:
        continue

    filepath = os.path.join(TEXT_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"🔍 Processing: {filename}")
    try:
        result = ask_claude(content[:8000])
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                print(f"⚠️ No valid JSON found in response for {filename}")
                continue

        parsed["filename"] = filename
        
        for col in COLUMNS:
            if col not in parsed:
                parsed[col] = None  
                
        data.append(parsed)
        time.sleep(1.5)  
    except Exception as e:
        print(f"❌ Error with {filename}: {e}")

if data:
    df = pd.DataFrame(data, columns=COLUMNS)  # type: ignore
    
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print(f"✅ Saved extracted results to {OUTPUT_CSV}")
    print("Sample of saved data:")
    print(df.head())
else:
    print("⚠️ No data was extracted - CSV file not created")