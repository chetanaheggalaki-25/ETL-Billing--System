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
        print(f"Testing {b_name}...")
        
        # Pick 2 random files from each batch folder
        files = [f for f in os.listdir(b_path) if f.lower().endswith(('.jpg', '.png'))]
        if not files: continue
        
        selected = files[:2] # Constant selection for deterministic testing
        
        for f in selected:
            fpath = os.path.join(b_path, f)
            try:
                text = converter.convert(fpath)
                extractor = MainExtractor(text)
                items = extractor.extract_line_items()
                
                # Success if some items were extracted (tabular) OR if it's gracefully handled
                status = "PASS" if items else "NON-TABULAR"
                row_count = len(items) if items else 0
                test_results.append({"File": f, "Batch": b_name, "Status": status, "Rows": row_count})
                print(f"  {f}: {status} ({row_count} rows)")
            except Exception as e:
                test_results.append({"File": f, "Batch": b_name, "Status": "FAIL", "Error": str(e)})
                print(f"  {f}: FAIL ({e})")

    # Save validation summary
    df = pd.DataFrame(test_results)
    print("\n--- Validation Summary ---")
    print(df.to_string())

if __name__ == "__main__":
    validate_across_batches()
