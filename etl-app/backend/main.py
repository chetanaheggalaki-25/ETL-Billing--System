import os
import shutil
import pandas as pd
import re
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
import pdfplumber
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
RULES_DIR = "rules"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RULES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

RULES_FILE = os.path.join(RULES_DIR, "inputfile_rules.xlsx")

if not os.path.exists(RULES_FILE):
    df_rules = pd.DataFrame(columns=["Field", "Pattern", "Type"])
    # Default header/footer rules
    default_rules = [
        {"Field": "Invoice No", "Pattern": r"(?i)invoice\s*(?:no|number)?[:.\s]*(\w+)", "Type": "Header"},
        {"Field": "Date", "Pattern": r"(?i)date[:.\s]*([\d\/-]+)", "Type": "Header"},
        {"Field": "Total", "Pattern": r"(?i)total[:.\s]*[^\d]*([\d,.]+)", "Type": "Footer"}
    ]
    pd.DataFrame(default_rules).to_excel(RULES_FILE, index=False)

def extract_text_from_file(file_path):
    text = ""
    if file_path.lower().endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    # Note: Images would need OCR (pytesseract), but we start with PDF for stability
    return text

def parse_with_rules(text):
    results = {}
    rules = pd.read_excel(RULES_FILE).to_dict(orient="records")
    
    for rule in rules:
        pattern = rule["Pattern"]
        match = re.search(pattern, text)
        if match:
            results[rule["Field"]] = match.group(1).strip()
        else:
            results[rule["Field"]] = "Not Found"
    return results

def extract_line_items(text):
    lines = text.split("\n")
    items = []
    # Improved regex for line items: matches [Descr] [Qty] [Price] [Total]
    # This is a generalized pattern for common invoice tables
    for line in lines:
        # Looking for lines with digits at the end (prices) and at least 3 parts
        match = re.search(r"(.+?)\s+(\d+)\s+([\d,.]+)\s+([\d,.]+)\s*$", line)
        if match:
            items.append({
                "Description": match.group(1).strip(),
                "Quantity": match.group(2),
                "Price": match.group(3),
                "Total": match.group(4)
            })
        elif any(keyword in line.lower() for keyword in ["tax", "subtotal", "gst", "vat"]):
            # Special handling for summary lines if needed
            continue
            
    # Fallback: if no 4-column table, try 2-column (Description + Price)
    if not items:
        for line in lines:
            match = re.search(r"(.+?)\s+([\d,.]+)\s*$", line)
            if match and any(char.isdigit() for char in line) and len(line.split()) > 1:
                items.append({
                    "Description": match.group(1).strip(),
                    "Amount": match.group(2)
                })
                
    return items

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        text = extract_text_from_file(file_path)
        if not text:
            return {"error": "Could not extract text. If this is an image, OCR may be required."}

        # 1. Extract Header/Footer using rules
        header_footer = parse_with_rules(text)
        
        # 2. Extract Line Items
        line_items = extract_line_items(text)
        
        # 3. Combine for Excel
        combined_data = []
        if line_items:
            for item in line_items:
                row = {**header_footer, **item}
                combined_data.append(row)
        else:
            combined_data.append({**header_footer, "Message": "No line items detected"})

        # Generate Output Excel
        output_filename = f"{os.path.splitext(file.filename)[0]}_main.xlsx"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        pd.DataFrame(combined_data).to_excel(output_path, index=False)

        return {
            "message": "Processed successfully",
            "download_url": f"/outputs/{output_filename}",
            "preview_data": combined_data[:5], # Send first 5 rows for UI preview
            "confidence": "High" if line_items else "Low (Manual check needed)"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/rules")
async def get_rules():
    if os.path.exists(RULES_FILE):
        return pd.read_excel(RULES_FILE).to_dict(orient="records")
    return []

@app.post("/rules/update")
async def update_rules(rules: List[dict]):
    pd.DataFrame(rules).to_excel(RULES_FILE, index=False)
    return {"message": "Rules updated"}

@app.get("/excel")
async def list_excels():
    files = os.listdir(OUTPUT_DIR)
    return [{"name": f, "url": f"/outputs/{f}"} for f in files]

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
app.mount("/previews", StaticFiles(directory=UPLOAD_DIR), name="previews")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
