import os
import pdfplumber
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
import pandas as pd

TENDER_DIR = "tenders/raw"
TEXT_DIR = "tenders/text"
os.makedirs(TEXT_DIR, exist_ok=True)

metadata = []

def extract_text_pdfplumber(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join([p.extract_text() or "" for p in pdf.pages])

def extract_text_ocr(path):
    images = convert_from_path(path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    return text

def is_scanned(path):
    doc = fitz.open(path)
    for page in doc:
        blocks = page.get_text("blocks")
        if any(b[4].strip() for b in blocks):
            return False
    return True

for filename in os.listdir(TENDER_DIR):
    if not filename.lower().endswith(".pdf"):
        continue

    full_path = os.path.join(TENDER_DIR, filename)
    print(f"Processing {filename}...")

    try:
        scanned = is_scanned(full_path)
        if not scanned:
            text = extract_text_pdfplumber(full_path)
            source = "digital"
        else:
            text = extract_text_ocr(full_path)
            source = "ocr"

        # Save extracted text
        text_file = os.path.join(TEXT_DIR, filename.replace(".pdf", ".txt"))
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(text)

        metadata.append({
            "filename": filename,
            "pages": fitz.open(full_path).page_count,
            "source": source,
            "text_len": len(text)
        })

    except Exception as e:
        print(f"❌ Error with {filename}: {e}")
        continue

# Save metadata
df = pd.DataFrame(metadata)
df.to_csv("tenders/metadata.csv", index=False)
print("✅ Extraction complete. Metadata saved.")
