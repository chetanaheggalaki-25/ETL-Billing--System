import os
import sys
import pandas as pd
from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor

DATA_DIR = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Bills"
OUTPUT_DIR = r"c:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\output"

def process_file(file_path):
    try:
        name = os.path.basename(file_path)
        converter = BillConverter()
        
        # 1. OCR to Text
        if file_path.lower().endswith(('.jpg', '.png', '.jpeg')):
            text = converter.image_to_text(file_path)
        else:
            text = converter.pdf_to_text(file_path)
            
        if not text.strip():
            return f"FAILED: No text extracted from {name}"

        # 2. Rule Generation: Get dynamic structural buckets
        generator = RuleGenerator(text)
        rules = generator.generate_rules()
        
        # 3. Extraction: Use the rules for 1:1 bucket alignment
        extractor = MainExtractor(text, rules)
        items = extractor.extract_line_items()
        
        # 4. Save
        base = os.path.splitext(name)[0]
        txt_path = os.path.join(OUTPUT_DIR, "txt", f"{base}.txt")
        rule_path = os.path.join(OUTPUT_DIR, "rules", f"{base}_rules.xlsx")
        xlsx_path = os.path.join(OUTPUT_DIR, "xlsx", f"{base}_items.xlsx")
        
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        os.makedirs(os.path.dirname(rule_path), exist_ok=True)
        os.makedirs(os.path.dirname(xlsx_path), exist_ok=True)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        if rules:
            pd.DataFrame(rules).to_excel(rule_path, index=False)
        if items:
            pd.DataFrame(items).to_excel(xlsx_path, index=False)
            
        return f"SUCCESS: {name} | Items: {len(items)}"
    except Exception as e:
        return f"ERROR: {os.path.basename(file_path)} | {str(e)}"

if __name__ == "__main__":
    files = sorted([f for f in os.listdir(DATA_DIR) if f.lower().endswith(('.jpg', '.png', '.pdf'))])
    # Process ALL files in the Billing folder for 100% coverage
    for f in files:
        print(process_file(os.path.join(DATA_DIR, f)))
    
    print("\nExhaustive batch processing of ALL billing files complete.")
