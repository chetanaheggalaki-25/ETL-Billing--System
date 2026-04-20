import os
import pandas as pd
import random
from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor

def batch_process():
    # Folder paths for comprehensive training
    folders_to_scan = [
        r"c:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Bills",
        r"c:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data"
    ]
    
    output_base = r"c:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\output"
    
    txt_dir = os.path.join(output_base, "txt")
    rules_dir = os.path.join(output_base, "rules")
    xlsx_dir = os.path.join(output_base, "xlsx")
    
    # 0. DEEP CLEAN
    print("--- Cleaning all previous outputs ---")
    for d in [txt_dir, rules_dir, xlsx_dir]:
        if os.path.exists(d):
            for f in os.listdir(d):
                try: 
                    os.remove(os.path.join(d, f))
                except: pass
        os.makedirs(d, exist_ok=True)
    
    # 1. Collect all PDF and Image files
    valid_exts = ('.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    bills_files = []
    data_files = []
    
    for base_folder in folders_to_scan:
        if os.path.exists(base_folder):
            for root, dirs, files in os.walk(base_folder):
                for file in files:
                    if file.lower().endswith(valid_exts):
                        path = os.path.join(root, file)
                        if "Bills" in base_folder:
                            bills_files.append(path)
                        else:
                            data_files.append(path)
    
    print(f"Found {len(bills_files)} in Bills and {len(data_files)} in Data.")
    # Take all from bills + 50 random from Data
    if len(data_files) > 50:
        data_files = random.sample(data_files, 50)
        
    all_files_to_process = bills_files + data_files
    print(f"Processing a sampled subset of {len(all_files_to_process)} bills total for testing.")
    
    converter = BillConverter()
    stats = {"processed": 0, "failed": 0, "no_items": 0}
    
    for idx, input_path in enumerate(all_files_to_process):
        filename = os.path.basename(input_path)
        belongs_to = next((b for b in folders_to_scan if input_path.startswith(b)), folders_to_scan[0])
        rel_path = os.path.relpath(input_path, belongs_to)
        
        base_name = os.path.basename(belongs_to)
        file_prefix = f"{base_name}_{rel_path.replace(os.sep, '_').replace(' ', '_')}"
        file_prefix = os.path.splitext(file_prefix)[0] 
        print(f"\n[{idx+1}/{len(all_files_to_process)}] Processing: {filename}")
        
        try:
            text_result = converter.convert(input_path)
            with open(os.path.join(txt_dir, f"{file_prefix}.txt"), "w", encoding="utf-8") as f:
                f.write(text_result)
            
            generator = RuleGenerator(text_result)
            rules = generator.generate_rules()
            if rules:
                df_rules = pd.DataFrame(rules)
                df_rules.to_excel(os.path.join(rules_dir, f"{file_prefix}_rules.xlsx"), index=False)
            
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
            print(f"   ERROR mapping {filename}: {e}")
            stats["failed"] += 1

    print("\n" + "="*50)
    print("UNIVERSAL TRAINING AND TESTING COMPLETE")
    print(f"Total Files Analyzed: {len(all_files_to_process)}")
    print(f"Extraction Successful (Found items): {stats['processed']}")
    print(f"No Items Found (Format anomaly): {stats['no_items']}")
    print("="*50)

if __name__ == "__main__":
    batch_process()
