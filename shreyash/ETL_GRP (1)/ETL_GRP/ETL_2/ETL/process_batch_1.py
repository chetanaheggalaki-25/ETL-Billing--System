import os
import pandas as pd
from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor
import warnings
warnings.filterwarnings('ignore')

def process_batch_1():
    scan_folder = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data\batch_1\batch_1"
    output_base = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\output"
    
    txt_dir = os.path.join(output_base, "txt")
    rules_dir = os.path.join(output_base, "rules")
    xlsx_dir = os.path.join(output_base, "xlsx")
    
    # Deep clean previous outputs
    print("--- Cleaning all previous outputs as requested ---")
    for d in [txt_dir, rules_dir, xlsx_dir]:
        if os.path.exists(d):
            for f in os.listdir(d):
                try: os.remove(os.path.join(d, f))
                except: pass
        os.makedirs(d, exist_ok=True)
        
    valid_img_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf')
    all_files = []
    
    for root, dirs, files in os.walk(scan_folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in valid_img_exts:
                all_files.append(os.path.join(root, f))
                
    # To avoid 1-hour wait times in a single operation, we'll process 100 random samples from batch1_1
    import random
    if len(all_files) > 100:
        all_files = random.sample(all_files, 100)

    print(f"Found files in batch_1/batch_1. Processing 100 subset natively...")
    
    stats = {"processed": 0, "failed": 0, "no_items": 0}
    converter = BillConverter()
    
    for idx, fpath in enumerate(all_files):
        filename = os.path.basename(fpath)
        base_name, ext = os.path.splitext(filename)
        
        print(f"\n[{idx+1}/{len(all_files)}] Processing natively: {filename}")
        
        file_prefix = base_name.replace(' ', '_')
        
        try:
            # 1. Convert to Text natively (Tesseract handles JPG pixels, eliminating Poppler PDF-extraction crashes)
            text_result = converter.convert(fpath)
            with open(os.path.join(txt_dir, f"{file_prefix}.txt"), "w", encoding="utf-8") as text_file:
                text_file.write(text_result)
                
            # 2. Train Rules (Analyze Structure)
            generator = RuleGenerator(text_result)
            rules = generator.generate_rules()
            if rules:
                df_rules = pd.DataFrame(rules)
                df_rules.to_excel(os.path.join(rules_dir, f"{file_prefix}_rules.xlsx"), index=False)
                
            # 3. Test Extraction (Extract Items)
            extractor = MainExtractor(text_result)
            items = extractor.extract_line_items()
            
            if items:
                df_items = pd.DataFrame(items)
                df_items.to_excel(os.path.join(xlsx_dir, f"{file_prefix}_main.xlsx"), index=False)
                print(f"   Done! Extracted {len(items)} items.")
                stats["processed"] += 1
            else:
                print(f"   No line items detected.")
                global_attrs = extractor.extract_document_attributes()
                fallback_df = pd.DataFrame([global_attrs]) if global_attrs else pd.DataFrame([{"Status": "No Data Extracted"}])
                fallback_df.to_excel(os.path.join(xlsx_dir, f"{file_prefix}_main.xlsx"), index=False)
                stats["no_items"] += 1
                
        except Exception as e:
            print(f"   ERROR processing {filename}: {e}")
            stats["failed"] += 1

    # Evaluation
    print("\n===============================")
    print("BATCH 1 (100 SAMPLE) EVALUATION COMPLETE")
    print(f"Total Processed: {len(all_files)}")
    print(f"Tabular Invoices Extracted: {stats['processed']}")
    print(f"Non-Tabular/Images: {stats['no_items']}")
    print(f"Failed to OCR: {stats['failed']}")
    print("===============================")

if __name__ == "__main__":
    process_batch_1()
