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

# Explicitly set output folders
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TXT_DIR = os.path.join(OUTPUT_DIR, "txt")
RULES_DIR = os.path.join(OUTPUT_DIR, "rules")
XLSX_DIR = os.path.join(OUTPUT_DIR, "xlsx")

# Candidate input folders as requested
INPUT_DIRS = [
    r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data\batch_1\batch_1\batch1_1",
    r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Bills"
]

# --- CONFIG ---
# Qwen 1.5B is significantly more accurate than 0.5B but still very fast and low-GPU
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct" 

def setup_cleaning():
    """Delete all previous outputs as requested."""
    print("🧹 Cleaning all previous outputs from txt, rules, and xlsx folders...")
    for d in [TXT_DIR, RULES_DIR, XLSX_DIR]:
        if os.path.exists(d):
            # Clean folder contents
            for filename in os.listdir(d):
                file_path = os.path.join(d, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
        else:
            os.makedirs(d, exist_ok=True)
    print("✅ System cleaned and ready.")

def init_llm():
    """Load a high-accuracy, low-GPU local LLM."""
    print(f"🚀 Loading High-Accuracy Local LLM ({MODEL_ID})...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype="auto", # auto handles quantization if 4-bit or 8-bit is requested or uses float16
        device_map="auto",
        low_cpu_mem_usage=True
    )
    generator = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=2048,
        return_full_text=False
    )
    return generator

def query_llm(generator, system_prompt, user_prompt):
    """Wrapper for LLM querying."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    output = generator(messages, max_new_tokens=2048)[0]['generated_text']
    return output

def extract_json(response):
    """Extract JSON array from LLM response safely."""
    clean = response.strip()
    match = re.search(r'\[.*\]', clean, re.DOTALL)
    if match:
        clean = match.group(0)
    try:
        data = json.loads(clean)
        return data if isinstance(data, list) else None
    except:
        return None

def load_knowledge_samples():
    """Load samples from the training dataset for few-shot boosting."""
    jsonl_path = os.path.join(ETL_DIR, "train_accurate_dataset.jsonl")
    samples = ""
    if os.path.exists(jsonl_path):
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for _ in range(3): # Take 3 samples to guide the model
                    line = f.readline()
                    if line:
                        obj = json.loads(line)
                        samples += f"\nExample Input:\n{obj.get('instruction','')[:500]}...\nExample Correct Output:\n{obj.get('output','')[:500]}...\n"
        except: pass
    return samples

def run_pipeline():
    # 1. Start clean
    setup_cleaning()
    
    # 2. Setup Tools
    generator = init_llm()
    converter = BillConverter()
    few_shot_context = load_knowledge_samples()
    
    # 3. Gather Files from both folders
    valid_exts = ('.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    all_files = []
    for d in INPUT_DIRS:
        if os.path.exists(d):
            print(f"🔍 Scanning: {d}")
            for f in os.listdir(d):
                if f.lower().endswith(valid_exts):
                    all_files.append(os.path.join(d, f))
    
    if not all_files:
        print(f"❌ No bills found in {INPUT_DIRS}")
        return

    print(f"📄 Found {len(all_files)} bills to process in high-accuracy mode.")
    
    # Global memory for rules (dynamic training inside)
    learned_rules = []

    # Processing Loop
    for idx, filepath in enumerate(all_files):
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]
        print(f"\n=======================================================")
        print(f"[{idx+1}/{len(all_files)}] Processing File: {filename}")
        print(f"=======================================================")

        # Step 1: Conversion
        try:
            raw_text = converter.convert(filepath)
            with open(os.path.join(TXT_DIR, f"{base_name}.txt"), "w", encoding="utf-8") as f:
                f.write(raw_text)
        except Exception as e:
            print(f"   -> Text Extraction Fail: {e}")
            continue

        text_preview = raw_text[:4000]
        correct = False
        
        while not correct:
            # Step 2: High-Accuracy Extraction
            print("   -> Running Master Extraction...")
            system_master = (
                "You are an Elite Data Extraction AI specialized in financial documents. "
                "Your task is to extract tabular line items from invoices with 100% precision. "
                "STRUCTURAL RULES:\n"
                "1. Look for rows that contain descriptions followed by numbers (Qty, Rate, Amount).\n"
                "2. If a description is split over multiple lines, merge it into a single 'Item' field.\n"
                "3. IGNORE summary lines like 'Total', 'GST TOTAL', 'Subtotal', or tax breakdown tables.\n"
                "4. Extract only the primary product/service lines.\n"
                "5. Ensure numbers are cleaned of currency symbols or extra spaces.\n"
                "Output ONLY a raw JSON array. Use keys: Item, Qty, Rate, Amount."
            )
            if learned_rules:
                system_master += "\nFOLLOW THESE LEARNED RULES:\n" + "\n".join([f"- {r}" for r in learned_rules])
            if few_shot_context:
                system_master += f"\nREFERENCE EXAMPLES:\n{few_shot_context}"
                
            user_prompt = f"Invoice Text:\n{text_preview}\n\nOutput JSON Array ONLY:"
            
            raw_output = query_llm(generator, system_master, user_prompt)
            data = extract_json(raw_output)
            
            if not data:
                print("   ❌ Extraction failed to produce JSON. Retrying...")
                continue
                
            # Show output to user for "check each and every one"
            print("\n----- EXTRACTED PREVIEW (First 3 items) -----")
            for item in data[:3]:
                print(item)
            print("------------------------------------------")
            
            # Interactive Check
            ans = input(f"🤔 Is this extraction correct? (y)es, (n)o and correct it, or (s)kip: ").strip().lower()
            
            if ans == 'y':
                correct = True
            elif ans == 's':
                print("⏭️ Skipping this file.")
                break
            elif ans == 'n':
                print("\n❌ Feedback received.")
                correction = input("Describe the error for correction (e.g. 'ignore subtotal line', 'Rate is after Qty'): ").strip()
                if correction:
                    learned_rules.append(correction)
                    print("🧠 Learning from correction and re-extracting...")
                else:
                    print("No feedback provided. Moving to next.")
                    break
            else:
                print("Invalid input. Proceeding.")
                correct = True

            # Step 4: Final save (only if correct)
            if correct and data:
                out_path = os.path.join(XLSX_DIR, f"{base_name}.xlsx")
                pd.DataFrame(data).to_excel(out_path, index=False)
                print(f"   ✨ Success! Saved to {out_path}")

    print("\n✅ All bills processed. System learned from your feedback.")

    print("\n✅ All bills processed. Accuracy enhanced. Outputs cleared and regenerated.")

if __name__ == "__main__":
    run_pipeline()
