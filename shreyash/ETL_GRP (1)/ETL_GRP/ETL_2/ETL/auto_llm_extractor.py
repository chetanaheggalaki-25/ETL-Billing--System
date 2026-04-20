import os
import json
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import warnings
import sys
import re

warnings.filterwarnings("ignore")

BASE_DIR = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2"
ETL_DIR = os.path.join(BASE_DIR, "ETL")
sys.path.append(ETL_DIR)
from bill_to_text import BillConverter

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TXT_DIR = os.path.join(OUTPUT_DIR, "txt")
RULES_DIR = os.path.join(OUTPUT_DIR, "rules")
XLSX_DIR = os.path.join(OUTPUT_DIR, "xlsx")

INPUT_DIRS = [
    os.path.join(BASE_DIR, "Data", "batch_1"),
    os.path.join(BASE_DIR, "Data", "batch_2"),
    os.path.join(BASE_DIR, "Bills")
]

def gather_files():
    valid_exts = ('.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    all_files = []
    seen = set()
    for d in INPUT_DIRS:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(valid_exts) and not f.endswith('.pdf.pdf'):
                        full_path = os.path.join(root, f)
                        if full_path not in seen:
                            seen.add(full_path)
                            all_files.append(full_path)
    return all_files

def extract_json(response, filename):
    clean = response.strip()
    match = re.search(r'\[.*\]', clean, re.DOTALL)
    if match:
        clean = match.group(0)
    try:
        data = json.loads(clean)
        return data, clean
    except Exception as e:
        print(f"Error parsing JSON for {filename}...")
        return None, clean

def init_llm():
    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    print("Loading LLM for automated extraction and self-reflection...")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype="auto", 
        device_map="auto",
        low_cpu_mem_usage=True
    )
    generator = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=1500,
        return_full_text=False
    )
    return generator

def query_llm(generator, system_prompt, user_prompt):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    output = generator(messages, max_new_tokens=1500)[0]['generated_text']
    return output

def main():
    print("Ensuring outputs folders exist...")
    for d in [TXT_DIR, RULES_DIR, XLSX_DIR]:
        os.makedirs(d, exist_ok=True)
        
    files = gather_files()
    if not files:
        print("No files discovered.")
        return
        
    print(f"Found {len(files)} files to process automatically.")
    
    # We will pick a small representative subset so it finishes quickly instead of taking hours,
    # prioritizing files from Data/batch_1 and batch_2
    import random
    random.shuffle(files)
    subset_files = files[:10]  # Process 10 files to demonstrate the capability quickly
    print(f"To ensure it finishes in less time (low GPU), processing 10 random bills...")
    
    generator = init_llm()
    converter = BillConverter()
    
    for idx, filepath in enumerate(subset_files):
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]
        print(f"\n--- [{idx+1}/{len(subset_files)}] Processing {filename} ---")
        
        try:
            raw_text = converter.convert(filepath)
            with open(os.path.join(TXT_DIR, f"{base_name}.txt"), "w", encoding="utf-8") as f:
                f.write(raw_text)
        except Exception as e:
            print(f"Failed extracting text: {e}")
            continue
            
        text_preview = raw_text[:3000] 
        
        # Phase 1: Initial Extraction
        system_1 = "You are an AI that extracts tabular line item data from raw invoice OCR text. Return ONLY a valid JSON array of objects representing the line items. Do NOT include subtotal, total, or tax from the footer! Use generic keys: Item, Qty, Rate, Amount."
        user_1 = f"Invoice Text:\n{text_preview}\n\nOutput JSON Array ONLY:"
        
        print("Phase 1: Generating Initial Extraction...")
        res_1 = query_llm(generator, system_1, user_1)
        data, json_str = extract_json(res_1, filename)
        
        if data is None:
            data = []
            json_str = "[]"
            res_1 = "Failed to output JSON"
            
        # Phase 2: Self-Reflection / Checking Output
        print("Phase 2: Checking if Extraction is Correct...")
        system_2 = "You are an AI Auditor. You check extracted JSON against the original invoice Text. Look out for formatting errors, missed columns, or accidental inclusion of 'Total', 'Subtotal', 'Tax' rows inside the line items. Output ONLY the word 'CORRECT' if there are no issues. If there is an issue, output 'ERROR: ' followed by the correction instructions."
        user_2 = f"Original Text:\n{text_preview}\n\nExtracted JSON:\n{json_str}\n\nIs it correct? Output 'CORRECT' or 'ERROR: <reason>'."
        
        res_2 = query_llm(generator, system_2, user_2)
        
        if "ERROR:" in res_2.upper():
            err_reason = res_2.split("ERROR:", 1)[1].strip() if "ERROR:" in res_2.upper() else res_2
            print(f"Issue found: {err_reason}")
            print("Phase 3: Correcting Output automatically...")
            
            # Phase 3: Correction Generation
            system_3 = f"You are an AI extractor. Your previous extraction had an error: {err_reason}. Please extract the line items again from the text, fixing this specific error. Return ONLY a valid JSON array."
            res_3 = query_llm(generator, system_3, user_1)
            final_data, _ = extract_json(res_3, filename)
            
            if final_data is not None:
                data = final_data
        else:
            print("Extraction deemed CORRECT on first attempt.")
            
        # Save output
        if data and isinstance(data, list):
            df = pd.DataFrame(data)
            out_path = os.path.join(XLSX_DIR, f"{base_name}.xlsx")
            df.to_excel(out_path, index=False)
            print(f"Saved {len(df)} rows to {out_path}")
        else:
            print("Failed to save output to XLSX. Invalid format.")

    print("\n✅ Automated LLM self-reflecting pipeline complete.")

if __name__ == "__main__":
    main()
