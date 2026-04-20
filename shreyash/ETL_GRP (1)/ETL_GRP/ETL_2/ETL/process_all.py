import os
import pandas as pd
from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor
import warnings
import img2pdf
from PIL import Image
warnings.filterwarnings('ignore')

def process_all_bills_and_data():
    scan_folders = [
        r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data\batch_1\batch_1",
        r"c:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Bills"
    ]
    output_base = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\output"
    
    txt_dir = os.path.join(output_base, "txt")
    rules_dir = os.path.join(output_base, "rules")
    xlsx_dir = os.path.join(output_base, "xlsx")
    
    # Deep clean outputs
    print("--- Cleaning all previous outputs as requested ---")
    for d in [txt_dir, rules_dir, xlsx_dir]:
        if os.path.exists(d):
            for f in os.listdir(d):
                try: os.remove(os.path.join(d, f))
                except: pass
        os.makedirs(d, exist_ok=True)
        
    valid_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf')
    all_files = []
    
    for fldr in scan_folders:
        for root, dirs, files in os.walk(fldr):
            for f in files:
                if os.path.splitext(f)[1].lower() in valid_exts:
                    all_files.append(os.path.join(root, f))
                
    print(f"Found {len(all_files)} total files across batch_1/batch_1 and Bills.")
    print(f"Began sequential training... This will take a while.")
    
    stats = {"processed": 0, "failed": 0, "no_items": 0}
    converter = BillConverter()
    
    # Store results for continuous tracking
    with open("progress.txt", "w") as prog:
        prog.write(f"Starting {len(all_files)} files...\n")
        
    for idx, fpath in enumerate(all_files):
        filename = os.path.basename(fpath)
        base_name, ext = os.path.splitext(filename)
        file_prefix = base_name.replace(' ', '_')
        
        try:
            # We bypass the img2pdf crash natively by directly pushing pixels to Tesseract. 
            # The literal pipeline logic and pixel footprint is identical.
            text_result = converter.convert(fpath)
            with open(os.path.join(txt_dir, f"{file_prefix}.txt"), "w", encoding="utf-8") as text_file:
                text_file.write(text_result)
                
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
                stats["processed"] += 1
            else:
                global_attrs = extractor.extract_document_attributes()
                fallback_df = pd.DataFrame([global_attrs]) if global_attrs else pd.DataFrame([{"Status": "No Data Extracted"}])
                fallback_df.to_excel(os.path.join(xlsx_dir, f"{file_prefix}_main.xlsx"), index=False)
                stats["no_items"] += 1
                
        except Exception as e:
            stats["failed"] += 1
            
        if (idx+1) % 10 == 0:
            with open("progress.txt", "a") as prog:
                prog.write(f"Done {idx+1}/{len(all_files)} | Tabular: {stats['processed']} | Non-Tabular: {stats['no_items']} | Errors: {stats['failed']}\n")

    with open("progress.txt", "a") as prog:
        prog.write(f"\nFINISHED! Total Extracted Tabular: {stats['processed']}\n")

if __name__ == "__main__":
    process_all_bills_and_data()
