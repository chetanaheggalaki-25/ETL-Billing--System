with open(r'..\output\txt\sample_test.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'TOTAL' in l.upper():
        print(f"--- LINE {i+1} ---")
        print("".join(lines[max(0, i-5):i+5]))
