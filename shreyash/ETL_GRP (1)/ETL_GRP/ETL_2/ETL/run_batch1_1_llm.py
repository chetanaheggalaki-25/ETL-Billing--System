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
from rule_generator import RuleGenerator
from main_extractor import MainExtractor

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TXT_DIR = os.path.join(OUTPUT_DIR, "txt")
RULES_DIR = os.path.join(OUTPUT_DIR, "rules")
XLSX_DIR = os.path.join(OUTPUT_DIR, "xlsx")

INPUT_DIRS = [
    r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data\batch_1\batch_1\batch1_1",
    r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Bills"
]

def init_llm():
    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    print("Loading Local LLM (Qwen 0.5B)...")
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

def extract_json(response, filename):
    clean = response.strip()
    match = re.search(r'\[.*\]', clean, re.DOTALL)
    if match:
        clean = match.group(0)
    try:
        data = json.loads(clean)
        return data
    except:
        return None

def process_pipeline():
    for d in [TXT_DIR, RULES_DIR, XLSX_DIR]:
        os.makedirs(d, exist_ok=True)
        # Deep clean as per instructions
        for f in os.listdir(d):
            try: os.remove(os.path.join(d, f))
            except: pass

    valid_exts = ('.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    all_files = []
    for d in INPUT_DIRS:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(valid_exts) and not f.endswith('.pdf.pdf'):
                        all_files.append(os.path.join(root, f))
    
    if not all_files:
        print(f"No files found in {INPUT_DIRS}")
        return

    print(f"Discovered {len(all_files)} files in total. Starting hybrid logic.")
    
    generator = init_llm()
    converter = BillConverter()

    for idx, filepath in enumerate(all_files):
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]
        print(f"\n[{idx+1}/{len(all_files)}] Processing {filename}...")

        # 1. Convert to TXT
        try:
            print(" -> Converting to .txt...")
            raw_text = converter.convert(filepath)
            txt_path = os.path.join(TXT_DIR, f"{base_name}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
        except Exception as e:
            print(f"Failed TXT conversion: {e}")
            continue

        # 2. Convert to Rules
        print(" -> Generating Contextual Rules...")
        rule_gen = RuleGenerator(raw_text)
        rules = rule_gen.generate_rules()
        rules_path = os.path.join(RULES_DIR, f"{base_name}_rules.xlsx")
        pd.DataFrame(rules).to_excel(rules_path, index=False)
        
        # 3. Refer to Rules & Generate XLSX using LLM for high accuracy checking
        print(" -> LLM High-Accuracy Extraction (Referencing Rules)...")
        rules_summary = "\n".join([f"{r['Field Name']}: Row {r['Row']}, ColRange {r['Column Start']}-{r['Column End']}" for r in rules if r['Section'] == 'COLUMNS'])
        
        # Original rigid extractor output as baseline
        rigid_items = []
        try:
            rigid_extractor = MainExtractor(raw_text)
            rigid_items = rigid_extractor.extract_line_items()
        except Exception as e:
            print(f"        (Legacy extractor crashed: {e})")
        
        text_preview = raw_text[:3000]
        
        # Use rigid extractor first to save CPU time
        data = rigid_items if rigid_items else []
        
        if not data:
            print(" -> Rigid extractor failed. Triggering slow LLM fallback...")
            system_1 = "You are a precise data extractor. Extract tabular line items safely into a JSON Array. Use the provided Rules (which specify headers/column bounds). Output ONLY a clean JSON array."
            user_1 = f"Rules Found:\n{rules_summary}\n\nInvoice Text:\n{text_preview}\n\nOutput JSON Array ONLY:"
            res_1 = query_llm(generator, system_1, user_1)
            data = extract_json(res_1, filename)
            if not data: data = []
        else:
            print(" -> Baseline extracted locally. Sending to LLM Auditor...")
        print(" -> Auditing and Correction Step (Checking output one by one)...")
        system_check = "You check the JSON Array of invoice line items exactly. Ensure there are no 'Total' or 'Tax' rows inside the lines. Output 'CORRECT' if perfect, or 'ERROR: [reason]' if flawed."
        user_check = f"Text:\n{text_preview}\n\nJSON:\n{json.dumps(data, indent=2)}\nReview it."
        
        check_res = query_llm(generator, system_check, user_check)
        
        if "ERROR:" in check_res.upper():
            print("    -> AI Auditor found flaw. Correcting output...")
            err = check_res.split("ERROR:", 1)[1].strip() if "ERROR:" in check_res.upper() else check_res
            sys_corr = f"Correct the extracting error. Previous attempt failed because: {err}. Output JSON Array ONLY."
            res_3 = query_llm(generator, sys_corr, user_1)
            corr_data = extract_json(res_3, filename)
            if corr_data:
                data = corr_data

        out_path = os.path.join(XLSX_DIR, f"{base_name}_main.xlsx")
        pd.DataFrame(data).to_excel(out_path, index=False)
        print(f" -> Generated final .xlsx: {out_path}")

if __name__ == "__main__":
    process_pipeline()
