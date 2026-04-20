import os
import json
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import warnings
import sys
import re
import shutil

warnings.filterwarnings("ignore")

# --- PATHS ---
BASE_DIR = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2"
ETL_DIR = os.path.join(BASE_DIR, "ETL")
sys.path.append(ETL_DIR)
from bill_to_text import BillConverter
from rule_generator import RuleGenerator

# Output folders
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TXT_DIR = os.path.join(OUTPUT_DIR, "txt")
RULES_DIR = os.path.join(OUTPUT_DIR, "rules")
XLSX_DIR = os.path.join(OUTPUT_DIR, "xlsx")

# Default Input Folder (All of Batch 1)
DEFAULT_INPUT = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data\batch_1"

# --- MODEL SELECTION ---
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct" 

def clean_outputs():
    """Wipes all previous data from txt, rules, and xlsx as requested."""
    print("🧹 Wiping previous outputs (txt, rules, xlsx)...")
    for d in [TXT_DIR, RULES_DIR, XLSX_DIR]:
        if os.path.exists(d):
            for filename in os.listdir(d):
                file_path = os.path.join(d, filename)
                try:
                    if os.path.isfile(file_path): os.unlink(file_path)
                    elif os.path.is_dir(file_path): shutil.rmtree(file_path)
                except Exception as e: print(f"Could not delete {file_path}: {e}")
        os.makedirs(d, exist_ok=True)
    print("✅ Slate is clean.")

def init_llm():
    """Initializes the local transformer pipeline."""
    print(f"🚀 Initializing High-Accuracy local model: {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
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

def query_llm(generator, system, user):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return generator(messages, max_new_tokens=1500)[0]['generated_text']

def extract_json(res):
    clean = res.strip()
    match = re.search(r'\[.*\]', clean, re.DOTALL)
    if match: clean = match.group(0)
    try:
        data = json.loads(clean)
        return data if isinstance(data, list) else None
    except: return None

def load_few_shot_examples():
    dataset_path = os.path.join(ETL_DIR, "train_accurate_dataset.jsonl")
    examples = ""
    if os.path.exists(dataset_path):
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i in [0, len(lines)//2, -1]:
                    obj = json.loads(lines[i])
                    examples += f"\nInput Sample:\n{obj.get('instruction','')[:300]}...\nOutput Sample:\n{obj.get('output','')[:300]}\n"
        except: pass
    return examples

def run_smart_pipeline(input_dir=None):
    # 1. Cleaning
    clean_outputs()
    
    # 2. Setup
    generator = init_llm()
    converter = BillConverter()
    few_shot = load_few_shot_examples()
    
    # 3. Discover
    valid_exts = ('.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    all_files = []
    search_dirs = [input_dir] if input_dir else [DEFAULT_INPUT]
    
    for d in search_dirs:
        if d and os.path.exists(d):
            print(f"🔍 Searching: {d}")
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(valid_exts) and not f.endswith('.pdf.pdf'):
                        all_files.append(os.path.join(root, f))
    
    if not all_files:
        print(f"❌ No bills found in: {search_dirs}")
        return

    print(f"📊 Total Bills Discovered: {len(all_files)}")
    
    # 4. Processing Loop
    for idx, filepath in enumerate(all_files):
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]
        print(f"\n--- [{idx+1}/{len(all_files)}] Processing: {filename} ---")
        
        # A. .txt output
        try:
            raw_text = converter.convert(filepath)
            txt_path = os.path.join(TXT_DIR, f"{base_name}.txt")
            with open(txt_path, "w", encoding="utf-8") as f: f.write(raw_text)
            print("   ✅ Text saved to txt/")
        except Exception as e:
            print(f"   ❌ Conversion Error: {e}")
            continue

        # B. rules output
        try:
            print("   -> Generating Rules...")
            rule_gen = RuleGenerator(raw_text)
            rules = rule_gen.generate_rules()
            rules_path = os.path.join(RULES_DIR, f"{base_name}_rules.xlsx")
            pd.DataFrame(rules).to_excel(rules_path, index=False)
            print("   ✅ Rules saved to rules/")
        except Exception as e:
            print(f"   ❌ Rule Generation Error: {e}")

        # C. .xlsx output (High-Accuracy LLM)
        print("   -> AI Extraction & Audit...")
        text_preview = raw_text[:3500]
        sys_p = "You are a precise data extractor. Extract line items into JSON. No tax/total rows."
        if few_shot: sys_p += f"\nSamples:\n{few_shot}"
        res = query_llm(generator, sys_p, f"Text:\n{text_preview}\n\nOutput JSON ONLY:")
        data = extract_json(res)
        
        if data:
            # Auditor Correction
            audit_sys = "You check for totals/errors in JSON. Output 'OK' or the corrected JSON array."
            audit_res = query_llm(generator, audit_sys, f"JSON:\n{json.dumps(data)}")
            corr = extract_json(audit_res)
            if corr: data = corr
            
            xlsx_path = os.path.join(XLSX_DIR, f"{base_name}_final.xlsx")
            pd.DataFrame(data).to_excel(xlsx_path, index=False)
            print("   ✅ Excel saved to xlsx/")
        else:
            print("   ⚠️ LLM failed to produce JSON.")

    print("\n✅ PROCESS COMPLETE. All files processed and sorted into txt, rules, and xlsx folders.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    run_smart_pipeline(target)
