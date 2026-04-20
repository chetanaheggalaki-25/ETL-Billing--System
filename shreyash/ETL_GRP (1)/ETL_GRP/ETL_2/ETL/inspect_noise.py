import pandas as pd
df = pd.read_excel(r"c:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\output\xlsx\main.xlsx")
noise_df = df[df.apply(lambda row: row.astype(str).str.contains('Page|Terms|Authorized Signatory|Goods once sold', case=False).any(), axis=1)]
with open("noise_check.txt", "w", encoding="utf-8") as f:
    f.write(noise_df.to_string())
print(f"Noise rows written to noise_check.txt. Total: {len(noise_df)}")
