import os
import shutil
import random
import pandas as pd
from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor

# CONFIGURATION
DATA_ROOT = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\Data"
OUTPUT_ROOT = r"C:\Users\SHREYAS R PATIL\OneDrive\Desktop\Aveenya_Intern\ETL_GRP (2)\ETL_GRP (1)\ETL_GRP\ETL_2\output"

TRAIN_DIR = os.path.join(DATA_ROOT, "Train")
TEST_DIR = os.path.join(DATA_ROOT, "Test")
VALID_DIR = os.path.join(DATA_ROOT, "Valid")

# RATIO (70/20/10)
RATIOS = {"Train": 0.70, "Test": 0.20, "Valid": 0.10}

def pool_current_data():
    """Moves all files from Train/Test/Valid back to a pool for a fresh shuffle."""
    print("Re-pooling files from existing splits for a fresh shuffle...")
    folders = [TRAIN_DIR, TEST_DIR, VALID_DIR]
    pool_dir = os.path.join(DATA_ROOT, "raw_pool")
    os.makedirs(pool_dir, exist_ok=True)
    
    for folder in folders:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    shutil.move(os.path.join(folder, f), os.path.join(pool_dir, f))
    print("Pooling complete.")

def split_data():
    """Finds all original bills and splits them 70/20/10 into Train/Test/Valid."""
    pool_current_data() # Ensure we start with a clean pool
    print("Scanning Data folders for original bills...")
    all_files = []
    
    # We scan raw_pool and generic batch folders 
    for root, dirs, files in os.walk(DATA_ROOT):
        # Skip existing split targets
        if any(x in root for x in ["Train", "Test", "Valid"]):
            continue
            
        for f in files:
            if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                all_files.append(os.path.join(root, f))
    
    print(f"Found {len(all_files)} files to partition.")
    if not all_files:
        print("No files discovered for re-splitting. (Check if they are already in Train/Test/Valid)")
        return
        
    random.shuffle(all_files)
    
    n_total = len(all_files)
    n_train = int(n_total * RATIOS["Train"])
    n_test = int(n_total * RATIOS["Test"])
    
    train_files = all_files[:n_train]
    test_files = all_files[n_train:n_train+n_test]
    valid_files = all_files[n_train+n_test:]
    
    # Physical Movement
    os.makedirs(TRAIN_DIR, exist_ok=True)
    os.makedirs(TEST_DIR, exist_ok=True)
    os.makedirs(VALID_DIR, exist_ok=True)
    
    print(f"Moving {len(train_files)} files to Train...")
    for f in train_files: shutil.move(f, os.path.join(TRAIN_DIR, os.path.basename(f)))
    
    print(f"Moving {len(test_files)} files to Test...")
    for f in test_files: shutil.move(f, os.path.join(TEST_DIR, os.path.basename(f)))
    
    print(f"Moving {len(valid_files)} files to Valid...")
    for f in valid_files: shutil.move(f, os.path.join(VALID_DIR, os.path.basename(f)))
    
    print("Splitting complete.")

def run_etl_on_directory(directory, limit=None):
    """Processes each bill in the directory through the ETL pipeline."""
    files = [f for f in os.listdir(directory) if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))]
    if limit:
        files = files[:limit]
        
    print(f"Running ETL on {len(files)} files in {os.path.basename(directory)}...")
    
    # Output structure
    txt_out = os.path.join(OUTPUT_ROOT, "txt")
    xlsx_out = os.path.join(OUTPUT_ROOT, "xlsx")
    rule_out = os.path.join(OUTPUT_ROOT, "rules")
    
    os.makedirs(txt_out, exist_ok=True)
    os.makedirs(xlsx_out, exist_ok=True)
    os.makedirs(rule_out, exist_ok=True)
    
    converter = BillConverter()
    
    for f in files:
        full_path = os.path.join(directory, f)
        name = os.path.splitext(f)[0]
        print(f" -> Processing: {f}")
        
        try:
            # 1. OCR (TXT)
            if f.lower().endswith('.pdf'):
                text = converter.pdf_to_text(full_path)
            else:
                text = converter.image_to_text(full_path)
                
            if not text.strip():
                print(f"  [X] Failed OCR for {f}")
                continue
                
            with open(os.path.join(txt_out, f"{name}.txt"), 'w', encoding='utf-8') as tf:
                tf.write(text)
            
            # 2. Rule Gen (RULES)
            generator = RuleGenerator(text)
            rules = generator.generate_rules()
            if rules:
                pd.DataFrame(rules).to_excel(os.path.join(rule_out, f"{name}_rules.xlsx"), index=False)
            
            # 3. Extraction (XLSX)
            extractor = MainExtractor(text, rules)
            items = extractor.extract_line_items()
            if items:
                pd.DataFrame(items).to_excel(os.path.join(xlsx_out, f"{name}_items.xlsx"), index=False)
            
            print(f"  [OK] Extraction complete for {f}")
            
        except Exception as e:
            print(f"  [ERROR] Processing {f}: {e}")

if __name__ == "__main__":
    split_data() # Move files to new split folders
    
    # We run ETL on Train/Test/Valid. 
    # For user verification, we run on the first few files of each to check quality.
    for folder in [TRAIN_DIR, TEST_DIR, VALID_DIR]:
        # Process ALL if explicitly requested, but usually better in chunks for verification.
        # User requested to "CHECK EACH AND EVERY OUTPUT", so I will run all of them or a significant batch.
        # Given 8000 files, we run it as a broad sweep.
        run_etl_on_directory(folder)
