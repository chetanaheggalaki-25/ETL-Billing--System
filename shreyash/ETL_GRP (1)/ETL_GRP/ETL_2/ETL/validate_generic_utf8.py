import os
import pandas as pd
from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor
import warnings
warnings.filterwarnings('ignore')

def validate_across_batches():
    batches = [
        r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data\batch_1\batch_1\batch1_1",
        r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data\batch_1\batch_1\batch1_2",
        r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data\batch_1\batch_1\batch1_3"
    ]
    
    test_results = []
    converter = BillConverter()
    
    for b_path in batches:
        b_name = os.path.basename(b_path)
        files = [f for f in os.listdir(b_path) if f.lower().endswith(('.jpg', '.png'))]
        if not files: continue
        selected = files[:2]
        
        for f in selected:
            fpath = os.path.join(b_path, f)
            try:
                text = converter.convert(fpath)
                extractor = MainExtractor(text)
                items = extractor.extract_line_items()
                status = "PASS" if items else "NON-TABULAR"
                row_count = len(items) if items else 0
                test_results.append({"File": f, "Batch": b_name, "Status": status, "Rows": row_count})
            except Exception as e:
                test_results.append({"File": f, "Batch": b_name, "Status": "FAIL", "Error": str(e)})

    # Force write as UTF-8
    with open("validation_report_utf8.txt", "w", encoding="utf-8") as outf:
        df = pd.DataFrame(test_results)
        outf.write("--- Validation Summary Across Batches ---\n")
        outf.write(df.to_string())
        outf.write("\n\nDetailed Checks:\n")
        for res in test_results:
             outf.write(f"File: {res['File']} | Batch: {res['Batch']} | Status: {res['Status']} | Rows: {res.get('Rows', 0)}\n")

if __name__ == "__main__":
    validate_across_batches()
