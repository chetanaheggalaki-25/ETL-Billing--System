import os
import json
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import warnings
import sys

warnings.filterwarnings("ignore")

# Define directories
BASE_DIR = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2"
ETL_DIR = os.path.join(BASE_DIR, "ETL")
sys.path.append(ETL_DIR)
from bill_to_text import BillConverter

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TXT_DIR = os.path.join(OUTPUT_DIR, "txt")
RULES_DIR = os.path.join(OUTPUT_DIR, "rules")
XLSX_DIR = os.path.join(OUTPUT_DIR, "xlsx")

# Candidate input folders
INPUT_FOLDERS = [
    os.path.join(BASE_DIR, "Bills"),
    os.path.join(BASE_DIR, "Data", "batch_1"),
    os.path.join(BASE_DIR, "Data", "batch_2")
]

def clean_outputs():
    print("🧹 Cleaning previous outputs...")
    for d in [TXT_DIR, RULES_DIR, XLSX_DIR]:
        if os.path.exists(d):
            for f in os.listdir(d):
                try: os.remove(os.path.join(d, f))
                except: pass
        os.makedirs(d, exist_ok=True)
    print("✅ All previous outputs deleted.")

def gather_files():
    valid_exts = ('.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    all_files = set()
    for folder in INPUT_FOLDERS:
        if os.path.exists(folder):
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(valid_exts) and not f.endswith('.pdf.pdf'):
                        all_files.add(os.path.join(root, f))
    return list(all_files)

def init_llm():
    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    print(f"🚀 Loading low-GPU LLM Model locally ({model_id})...")
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
        max_new_tokens=1024,
        return_full_text=False
    )
    return generator

def main():
    # 1. Clean old outputs
    clean_outputs()
    
    # 2. Get bills
    files = gather_files()
    if not files:
        print("❌ No bills found in batch 1, batch 2 or Bills folders.")
        return
        
    print(f"\n📄 Found {len(files)} bills to process.")
    
    # 3. Setup LLM and Converter
    generator = init_llm()
    converter = BillConverter()
    
    # Global 'memory' for dynamic learning
    learned_rules = []
    
    import re
    
    for idx, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]
        print(f"\n=======================================================")
        print(f"[{idx+1}/{len(files)}] Processing File: {filename}")
        print(f"=======================================================")
        
        # Extract text
        try:
            print("📝 Extracting text...")
            raw_text = converter.convert(filepath)
            with open(os.path.join(TXT_DIR, f"{base_name}.txt"), "w", encoding="utf-8") as f:
                f.write(raw_text)
        except Exception as e:
            print(f"⚠️ Text extraction failed for {filename}: {e}")
            continue
            
        # Clean up text length if too long (take the most relevant part or just truncate safely)
        text_preview = raw_text[:3000] # Qwen has 32k context, but 3000 characters is safe for 0.5B to avoid OOM
        
        correct = False
        while not correct:
            print("\n🤖 Running LLM extraction...")
            
            # Construct Prompt
            system_prompt = (
                "You are an expert data extractor. Extract the line items from the invoice text below into a JSON array of objects. "
                "Each object should have keys like 'ItemDescription', 'Quantity', 'Rate', 'Amount'. "
                "Output ONLY a raw JSON array. DO NOT output markdown formatting like ```json. Just the [ ... ] structure."
            )
            
            if learned_rules:
                system_prompt += "\nCRITICAL RULES TO FOLLOW BASED ON PAST CORRECTIONS:\n"
                for rule in learned_rules:
                    system_prompt += f"- {rule}\n"
                    
            user_prompt = f"INVOICE TEXT:\n{text_preview}\n\nOUTPUT ONLY THE EXTRACTED JSON ARRAY:"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            output = generator(messages, max_new_tokens=1024)[0]['generated_text']
            
            clean_output = output.strip()
            if clean_output.startswith("```json"):
                clean_output = clean_output[7:]
            if clean_output.startswith("```"):
                clean_output = clean_output[3:]
            if clean_output.endswith("```"):
                clean_output = clean_output[:-3]
            clean_output = clean_output.strip()
            
            print("\n============ LLM EXTRACTED OUTPUT ============")
            print(clean_output)
            print("==============================================")
            
            ans = input(f"\n🤔 Is this correct for {filename}? (y)es, (n)o and correct it, or (s)kip: ").strip().lower()
            
            if ans == 'y':
                correct = True
                print("✅ Marked as correct. Saving to XLSX...")
                # Try saving
                try:
                    data = json.loads(clean_output)
                    if isinstance(data, list) and data:
                        df = pd.DataFrame(data)
                        df.to_excel(os.path.join(XLSX_DIR, f"{base_name}.xlsx"), index=False)
                    else:
                        print("⚠️ Not a list or empty.")
                except Exception as e:
                    print(f"⚠️ Could not parse JSON to excel: {e}")
            elif ans == 's':
                print("⏭️ Skipping this file.")
                break
            elif ans == 'n':
                print("\n❌ Extraction incorrect.")
                correction = input("Describe what the model did wrong so it can learn (e.g. 'ignore total amounts at bottom', 'extract HSN codes'): ").strip()
                if correction:
                    learned_rules.append(correction)
                    print("🧠 Rule added to memory! Re-running extraction for this bill with the new learning...")
                else:
                    print("No rule provided, skipping.")
                    break
            else:
                print("Invalid input. Skipping.")
                break

if __name__ == "__main__":
    main()
