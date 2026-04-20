import pandas as pd
import os

path = r'C:\Users\Chetana\Downloads\dummy\shreyash\ETL_GRP (1)\ETL_GRP\ETL_2\output\xlsx\batch1-0050.jpg_extracted.xlsx'
if os.path.exists(path):
    try:
        df = pd.read_excel(path)
        print("SUCCESS: File is a valid Excel file.")
        print("Rows:", len(df))
        print("Columns:", df.columns.tolist())
    except Exception as e:
        print("FAILURE:", e)
else:
    print("FILE NOT FOUND")
