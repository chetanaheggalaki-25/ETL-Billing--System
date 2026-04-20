import os
import shutil
import pandas as pd
import time
from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor

# CONFIGURATION
DATA_ROOT = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2"
OUTPUT_ROOT = os.path.join(DATA_ROOT, "output")

def run_universal_etl():
    """Finds all original bills in Data folder (recursively) and executes the full extraction suite."""
    print("Initializing Universal ETL Pipeline...")
    
    # 0. Clean Start (Total Reset per User Request)
    if os.path.exists(OUTPUT_ROOT):
        try:
            shutil.rmtree(OUTPUT_ROOT)
            print("  [CLEANUP] Deleted previous outputs for fresh processing.")
        except:
            pass
    
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    
    # 1. Prepare Output Structure
    txt_out = os.path.join(OUTPUT_ROOT, "txt")
    xlsx_out = os.path.join(OUTPUT_ROOT, "xlsx")
    rule_out = os.path.join(OUTPUT_ROOT, "rules")
    
    os.makedirs(txt_out, exist_ok=True)
    os.makedirs(xlsx_out, exist_ok=True)
    os.makedirs(rule_out, exist_ok=True)
    
    # 2. Discover All Bills in "Bills" and "pdf" folders
    input_dirs = [
        os.path.join(DATA_ROOT, "Bills"),
        os.path.join(DATA_ROOT, "pdf")
    ]
    all_files = []
    for target_dir in input_dirs:
        if os.path.exists(target_dir):
            for root, dirs, files in os.walk(target_dir):
                for f in files:
                    if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                        full_path = os.path.join(root, f)
                        # ensure we aren't picking up cache files
                        if not f.endswith('.pdf.pdf') and "temp_" not in f:
                            all_files.append(full_path)
    
    n_total = len(all_files)
    print(f"Discovered {n_total} bills for processing.")
    
    converter = BillConverter()
    success_count = 0
    start_time = time.time()
    
    # 3. Process Each Bill
    for i, full_path in enumerate(all_files):
        f = os.path.basename(full_path)
        name = os.path.splitext(f)[0]
        
        # Calculate Progress
        elapsed = time.time() - start_time
        pct = (i / n_total) * 100 if n_total > 0 else 0
        
        print(f"[{i+1}/{n_total}] ({pct:.1f}%) -> Processing: {f}")
        
        try:
            # A. Robust Multi-Method OCR (TXT)
            text = converter.convert(full_path)
                
            if not text.strip():
                print(f"  [EMPTY OCR] {f}")
                continue
                
            with open(os.path.join(txt_out, f"{name}.txt"), 'w', encoding='utf-8') as tf:
                tf.write(text)
            
            # B. Rule Identification (RULES)
            generator = RuleGenerator(text)
            rules = generator.generate_rules()
            if rules:
                pd.DataFrame(rules).to_excel(os.path.join(rule_out, f"{name}_rules.xlsx"), index=False)
            
            # C. Transaction Extraction (XLSX)
            extractor = MainExtractor(text, rules)
            # Pass the coordinate map for the 'Robot with a Ruler' strategy
            word_map = getattr(converter, 'word_map', None)
            items = extractor.extract_line_items(word_map)
            if items:
                items_df = pd.DataFrame(items)
                # Column Pruning: Drop columns that are 100% blank
                items_df.replace("", pd.NA, inplace=True)
                items_df.dropna(axis=1, how='all', inplace=True)
                items_df.fillna("", inplace=True)
                
                if not items_df.empty:
                    items_df.to_excel(os.path.join(xlsx_out, f"{name}_items.xlsx"), index=False)
                    # PRD Compliance: Save CSV output
                    csv_out = os.path.join(OUTPUT_ROOT, "csv")
                    os.makedirs(csv_out, exist_ok=True)
                    items_df.to_csv(os.path.join(csv_out, f"{name}_items.csv"), index=False)
                    success_count += 1
                    print(f"   [RULER EXTRACTED] Items: {len(items)}")
            else:
                print(f"   [NO ITEMS] {f}")
            
        except Exception as e:
            import traceback
            print(f"   [ERROR] {f}: {e}")
            print(traceback.format_exc())

    final_time = time.time() - start_time
    print(f"\nCOMPLETED! Processed {success_count}/{n_total} bills successfully in {final_time:.1f}s.")

if __name__ == "__main__":
    run_universal_etl()
