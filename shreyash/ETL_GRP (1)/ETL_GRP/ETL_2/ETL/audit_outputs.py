import os
import pandas as pd
import re

OUTPUT_XLSX = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\output\xlsx"

def audit():
    if not os.path.exists(OUTPUT_XLSX):
        print("Output folder not found.")
        return

    files = [f for f in os.listdir(OUTPUT_XLSX) if f.endswith('.xlsx')]
    print(f"Auditing {len(files)} files...\n")

    for f in files:
        path = os.path.join(OUTPUT_XLSX, f)
        try:
            df = pd.read_excel(path)
            if df.empty: continue
            
            issues = []
            for col in df.columns:
                col_up = str(col).upper()
                
                # Check for alphabet soup in numeric columns
                if any(x in col_up for x in ["QTY", "RATE", "PRICE", "AMOUNT", "VALUE"]):
                    # Filter out NaN/nulls and 'nan' string
                    col_vals = df[col].dropna().astype(str)
                    col_vals = col_vals[col_vals.str.lower() != 'nan']
                    
                    text_rows = col_vals[col_vals.str.contains(r'[a-zA-Z]{3,}', na=False)]
                    if len(text_rows) > 0:
                        issues.append(f"Column '{col}' contains words: {text_rows.tolist()[:2]}")
                
            if issues:
                print(f"FILE: {f}")
                for issue in issues:
                    print(f"  [!] {issue}")
                print("-" * 30)

        except Exception as e:
            print(f"Error reading {f}: {e}")

if __name__ == "__main__":
    audit()
