import re
import pandas as pd

try:
    from rule_generator import RuleGenerator
except ImportError:
    class RuleGenerator:
        def __init__(self, text): self.text_content = text
        def generate_rules(self): return []
        def segment(self): return 0, len(self.text_content.split('\n'))


def clean_name(text):
    """Clean attribute names to be literal as found in doc."""
    if not text: return None
    return text.strip()




class MainExtractor:
    def __init__(self, text_content, rules=None):
        self.text_content = text_content
        self.rules = rules if rules is not None else []
        self.lines = [line.rstrip() for line in text_content.split('\n')]
        
        # NLP model removed to prevent DLL conflicts
        self.nlp = None
            
        # Expanded rejection keywords for multi-page bills and explicitly ignored sections
        self.rejection_kws = [
            "PAGE ", "PAGENO", "OF ", "TERMS", "CONDITION", "SIGNED", "SIGNATORY", "AUTHORIZED", 
            "GOODS ONCE", "NOT REFUNDABLE", "BANK DETAILS", "SWIFT", 
            "REMITTANCE", "DECLARATION", "VAT NO", "CIN NO", "OFFICE",
            "SUMMARY", "DISCOUNT", "TAXABLE", "ROUND OFF", "THOUSAND", "RUPEES", "ONLY", "PAISA",
            "THIRTY", "FIFTY", "HUNDRED", "TWELVE", "THIRTEEN", "FOURTEEN", 
            "E & O.E", "E.O.E", "THANK YOU", "TOTAL", "SUBTOTAL"
        ]
        
        # Unique Identifiers prioritized for Rules and Excel output
        self.important_attrs = ["GSTIN", "PAN", "ACCOUNT", "IFSC", "IBAN", "SWIFT", "INVOICE", "DATE"]

    def _get_metrics(self, line):
        stripped = line.strip()
        if not stripped: return {'tokens': [], 'has_num': False, 'raw': line, 'is_sep': False}
        # Conservative tokenization: only 1 or 2 spaces allowed within a single field token
        # This prevents 'Unit' and 'Price' from merging if they are close.
        tokens = [m for m in re.finditer(r'\S+(?:\s{1,2}\S+)*', line)]
        has_num = bool(re.search(r'[\d,\|\./]{1,10}[,\.\|/]\d{1,4}\b|\b\d{2,}\b', stripped))
        is_sep = bool(re.fullmatch(r'[\s=\-_*#~]+', stripped))
        return {'tokens': tokens, 'has_num': has_num, 'raw': line, 'is_sep': is_sep}

    def extract_document_attributes(self, word_map=None):
        """Metadata Extraction: Prioritizes Rules-based and Spatial discovery."""
        attrs = {}
        rule_fields = set()
        
        # 1. Rules-First Extraction (Propagate from RuleGenerator & Manual Edits)
        if self.rules:
            for r in self.rules:
                if r.get('Section') in ['HEADER', 'FOOTER']:
                    field = r.get('Field Name')
                    val = r.get('Sample Text')
                    if val and field:
                        attrs[field] = val
                        # Mark this field as handled to prevent regex fallback duplication
                        rule_fields.add(field.upper().replace(" ", "_").replace(":", ""))

        # 2. Spatial 'Robot with a Ruler' (Refinement if map available)
        if word_map and self.rules:
            print("  [RULER] Refining document attributes via coordinate anchors...")
            for r in self.rules:
                if r.get('Section') in ['HEADER', 'FOOTER']:
                    field = r.get('Field Name')
                    keyword = r.get('Keyword Start')
                    
                    if not attrs.get(field): # Only search if not already found by RuleGen regex
                        anchor = None
                        if keyword:
                            keyword_str = str(keyword).lower()
                            for w in word_map:
                                if keyword_str in w['text'].lower():
                                    anchor = w
                                    break
                        
                        if anchor:
                            val_parts = []
                            for w in word_map:
                                if abs(w['y0'] - anchor['y0']) < 15 and w['x0'] > anchor['x1'] - 5:
                                    if w != anchor: val_parts.append(w['text'])
                            
                            if val_parts:
                                attrs[field] = " ".join(val_parts).strip().lstrip(":.- ")

        # 3. Comprehensive Regex Fallback (The 'Safety Net')
        dynamic_attrs = self._extract_regex_fallback()
        for k, v in dynamic_attrs.items():
            norm_k = k.upper().replace(" ", "_").replace(":", "")
            if not attrs.get(k) and norm_k not in rule_fields:
                attrs[k] = v
        
        return attrs

    def _extract_regex_fallback(self):
        attrs = {}
        
        def norm_date(val):
            val = re.sub(r'^(?:of\s+issue|Date|DATED)[:.\s]*', '', val, flags=re.I).strip()
            val = re.split(r'\s+of\s+issue', val, flags=re.I)[0].strip()
            return val.rstrip(":.- ")
            
        def norm_bank(val):
            val = val.replace("back", "Bank").strip()
            return re.sub(r'[\s\-:|]{2,}', ' ', val).strip()
        def norm_none(val):
            return val.rstrip(":.- ")

        # Header substring regex, Expected Value format regex, Field Name, Normalizer
        patterns = [
            (r'\b(?:INVOICE|BILL|MEMO)\s*(?:NO|#|NUM|NUMBER)\b|\b(?:INVOICE|BILL|MEMO)\s*[:\-]', r'((?!\d{2,4}[\/\-]\d{2}[\/\-]\d{2,4})[A-Za-z0-9\-/]{5,25})', "Invoice_No", norm_none),
            (r'(?:DATE|DATED|DATE\s+OF\s+ISSUE)', r'([\d\-/]{8,12}|(?:[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})|(?:\d{1,2}\s+[a-zA-Z]{3,9}\s+\d{2,4}))', "Invoice_Date", norm_date),
            (r'(?:GSTIN|VAT|TAX\s*ID|TAX\s*LD)', r'([0-9]{2}[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}[1-9A-Za-z]{1}Z[0-9A-Za-z]{1}|[A-Za-z0-9 \-]{10,20})', "Seller_GSTIN", norm_none),
            (r'PAN', r'([A-Z]{5}[0-9]{4}[A-Z]{1})', "Seller_PAN", norm_none),
            (r'(?:ACCOUNT|ACC|A/C)', r'([0-9\-/]{10,22})', "Bank_Account", norm_none),
            (r'IFSC', r'([A-Z]{4}0[A-Z0-9]{6})', "Bank_IFSC", norm_none),
            (r'IBAN', r'([A-Z]{2}[0-9]{2}[A-Z0-9]{12,30})', "Bank_IBAN", norm_none),
        ]

        full_text = self.text_content
        for header_pattern, value_pattern, label, normalizer in patterns:
            for match in re.finditer(header_pattern, full_text, flags=re.I):
                header_end = match.end()
                # Strict Horizontal Scanning: Only look to the right side on the same line
                raw_search = full_text[header_end : header_end + 80]
                search_area = raw_search.split('\n')[0] if '\n' in raw_search else raw_search
                
                # Analyze for delimiters and formats
                # 1. Skip colons/dashes/labels like 'No'
                search_area = re.sub(r'^(?:[\s\.:\-\#]|NO|NUM|NUMBER|DATE|OF|ISSUE)+', '', search_area, flags=re.I).strip()
                
                # 2. Match the specific format
                val_match = re.search(value_pattern, search_area, flags=re.I)
                if val_match:
                    val = val_match.group(1).strip()
                    val = normalizer(val)
                    
                    # Filtering noise
                    noise = ["REGISTER", "JOURNAL", "LISTING", "REPORT", "SAMPLES", "DOCUMENT", "PAGE", "WORDS ONLY", "THOUSAND", "LAKH", "ORIGINAL", "DUPLICATE", "TRIPLICATE", "RECIPIENT", "TRANSPORTER", "SUPPLIER"]
                    if any(n in val.upper() for n in noise) and len(val) < 25: continue
                    
                    if label == "Invoice_No":
                        if re.search(r'^\d{1,2}[\/\-\.\s]{1,2}(?:[a-zA-Z]{3,9}|\d{1,2})[\/\-\.\s]{1,2}\d{2,4}$', val.strip()):
                            continue
                    
                    attrs[label] = val
                    break # Stop after first successful match for this attribute
        return attrs

    def extract_line_items(self, word_map=None):
        """Universal extraction with dynamic column anchoring and global metadata propagation."""
        # 1. First, get the structural rules for this specific bill ONLY IF not provided
        if not self.rules:
            generator = RuleGenerator(self.text_content)
            self.rules = generator.generate_rules()
            h_end, f_start_idx = generator.segment()
        
        global_info = self.extract_document_attributes(word_map)
        
        metrics = [self._get_metrics(l) for l in self.lines]
        # 2. Extract column boundaries from the rules
        # RuleGenerator uses 'Rule type', 'Field Name', 'Column Start', 'Column End'
        current_cols = []
        table_start_idx = 0
        f_start_idx = len(metrics)
        
        if self.rules:
            for r in self.rules:
                if r.get('Section') == 'COLUMNS':
                    current_cols.append({
                        'label': r.get('Field Name', 'Col').replace("Col: ", ""),
                        'start': int(r.get('Column Start', 0)),
                        'end': int(r.get('Column End', 0))
                    })
                # SYNC Item Start and Footer boundary
                if r.get('Section') == 'STRUCTURE' and r.get('Field Name') == 'Line Item Start':
                    # Row in rules is 1-indexed. e.g. Row 12 (index 11).
                    table_start_idx = int(r.get('Sample Text', 0)) - 1
                if r.get('Section') == 'STRUCTURE' and r.get('Field Name') == 'Footer Start':
                    f_start_idx = int(r.get('Sample Text', 0)) - 1
        
        # --- Rule-Based Structural Anchoring ---
        if self.rules:
            for r in self.rules:
                if r.get('Section') == 'COLUMNS':
                    current_cols.append({
                        'label': r.get('Field Name', 'Col'),
                        'start': int(r.get('Column Start', 0)),
                        'end': int(r.get('Column End', 0))
                    })
                if r.get('Section') == 'STRUCTURE' and r.get('Field Name') == 'Line Item Start':
                    table_start_idx = int(r.get('Sample Text', 0)) - 1
                if r.get('Section') == 'STRUCTURE' and r.get('Field Name') == 'Footer Start':
                    f_start_idx = int(r.get('Sample Text', 0)) - 1
                
                # Capture all important metadata from rules (Header/Footer/Primary Identifiers)
                if r.get('Section') in ['HEADER', 'FOOTER'] or r.get('Field Name') in self.important_attrs:
                    global_info[r.get('Field Name')] = r.get('Sample Text')
        
        # --- 50-Epoch Structural Training / Column Evolution ---
        if not current_cols:
            best_temp_cols = []
            best_score = -1
            
            # --- High-Precision Column Seeding (Header-Based) ---
            header_line_idx = -1
            # Search for the header line within a small window above the table
            for search_idx in range(table_start_idx - 1, max(-1, table_start_idx - 5), -1):
                if 0 <= search_idx < len(self.lines):
                    line_text = self.lines[search_idx]
                    if any(k in line_text.upper() for k in ["DESC", "ITEM", "QTY", "RATE", "AMOUNT", "PRICE", "VAT", "HSN"]):
                        header_line_idx = search_idx
                        break
            
            header_tokens = []
            if header_line_idx != -1:
                header_tokens = [m for m in re.finditer(r'\S+(?:\s{1,3}\S+)*', self.lines[header_line_idx])]

            for epoch in range(1, 51):
                # Adaptive tolerance for gutter identification
                tol = 1.0 + (epoch * 0.05) if epoch > 25 else 1.2
                x_density = [0] * 1024
                
                for i in range(max(0, table_start_idx), min(len(metrics), f_start_idx)):
                    m = metrics[i]
                    if not m['is_sep']:
                        for t in m['tokens']:
                            # Weight tokens by numeric importance - numeric tokens define pillar stability
                            weight = 5 if bool(re.search(r'\d', t.group(0))) else 1
                            for pos in range(t.start(), t.end()):
                                if pos < 1024: x_density[pos] += weight
                
                # Discover Gutters
                gutters = []
                cur_g = None
                for x in range(len(x_density)):
                    if x_density[x] == 0:
                        if cur_g is None: cur_g = [x, x]
                        else: cur_g[1] = x
                    else:
                        if cur_g is not None:
                            if (cur_g[1] - cur_g[0]) >= round(tol): gutters.append(cur_g)
                            cur_g = None
                
                temp_cols = []
                lx = 0
                for g in gutters:
                    if g[0] > lx + 1: temp_cols.append({'start': lx, 'end': g[0]})
                    lx = g[1]
                temp_cols.append({'start': lx, 'end': 1024})
                
                # Fitness Score with Header Anchoring
                score = 0
                for i in range(max(0, table_start_idx), min(len(metrics), f_start_idx)):
                    distribution = [0] * len(temp_cols)
                    for t in metrics[i]['tokens']:
                        ctr = t.start() + (len(t.group(0))/2)
                        for k, c in enumerate(temp_cols):
                            if c['start'] <= ctr < c['end']: distribution[k]+=1
                    if sum(1 for b in distribution if b > 0) >= round(len(temp_cols) * 0.7): score += 1
                
                # Bonus for column count matching header count
                if header_tokens and len(temp_cols) == len(header_tokens): score += 10

                if score > best_score:
                    best_score = score
                    best_temp_cols = temp_cols
            
            # Finalize Optimal Structural Columns
            for j, c in enumerate(best_temp_cols):
                label = f"Column_{j+1}"
                if header_tokens:
                    # Anchor matching: find header token that overlaps with this column's physical span
                    for ht in header_tokens:
                        ht_ctr = (ht.start() + ht.end()) / 2
                        if c['start'] - 3 <= ht_ctr <= c['end'] + 3:
                            label = ht.group(0).strip()
                            break
                            
                reject_kws = ["sr", "no.", "cess", "gst", "cgst", "sgst", "igst"]
                if any(label.lower() == k or k in label.lower() for k in reject_kws) and len(label) < 8:
                    continue
                
                current_cols.append({'label': label, 'start': c['start'], 'end': c['end']})
            print(f"  [TRAINING] Completed 50 structural epochs. Best Score: {best_score}")

        # Now process the table starting from the actual data line until the footer starts
        all_items = []
        last_item = None
        for i in range(max(0, table_start_idx), min(len(metrics), f_start_idx)):
            m = metrics[i]
            # Initialize loop flags
            raw_upper = m['raw'].upper()
            
            # 1. Robust Page-Break & Footer Rejection (Added Invoice/Metadata words)
            noise_kws = ["PAGE ", "AUTHORIZED SIGNATORY", "AUTHORISED SIGNATORY", "SIGNATURE", "TERMS", "GOODS ONCE SOLD", "NOT REFUNDABLE", "THANK YOU", "REMITTANCE", "DECLARATION", "===== ", "----- ", "INVOICE NO", "PLACE OF SUPPLY", "TAX INVOICE", "BILL TO", "SHIP TO", "GSTIN", "STATE INFO"]
            is_noise = any(nk in raw_upper for nk in noise_kws) or m['is_sep']
            
            if is_noise:
                continue

            # 2. Repeated Header Detection (Skip column name repetitions on next pages)
            header_hits = 0
            for c in current_cols:
                # Basic label matching without spaces to catch fused OCR headers
                clean_lbl = re.sub(r'[^A-Z]', '', c['label'].upper())
                clean_raw = re.sub(r'[^A-Z]', '', raw_upper)
                if len(clean_lbl) > 2 and clean_lbl in clean_raw:
                    header_hits += 1
            
            if header_hits >= 3 and i > table_start_idx + 2:
                # We skip repeated headers, but we don't break the loop as more items follow below
                continue

            # Strengthened summary detection: reject lines that look like summary headers or totals
            # We differentiate between "Sub-Totals" (to skip) and "Hard Terminals" (to break)
            is_summary_line = any(rk in raw_upper for rk in ["TOTAL", "SUBTOTAL", "SUMMARY", "VAT [%]", "NET WORTH", "GROSS WORTH", "TAXABLE AMOUNT", "ROUND OFF", "GST %", "SGST", "CGST", "IGST"])
            
            # Contextual Summary Check: Does it look like a floating summary row?
            has_percent = "%" in raw_upper or "@" in raw_upper
            has_long_text = any(len(t.group(0)) > 12 for t in m['tokens'])
            if has_percent and not has_long_text and not any(k in raw_upper for k in ["DESC", "ITEM", "NAME"]):
                 is_summary_line = True

            if is_summary_line:
                # If we encounter a Grand Total or heavy summary, we consider the table ended
                if any(rk in raw_upper for rk in ["GRAND TOTAL", "TOTAL AMOUNT", "TOTAL (INR)", "TOTAL (RS)", "NET PAYABLE"]):
                     break
                continue
            
            has_dec = bool(re.search(r'[\d,\|\./]{1,10}[,\.\|/]\d{2,4}\b', m['raw']))
            
            # TRANSACTIONAL GATING (Contextual Boundary Strategy)
            if is_summary_line and not (has_dec and len(m['tokens']) > 8):
                # Hard-break ONLY at categorical document boundaries (Footers)
                hard_terminals = ["TERMS AND", "DECLARATION", "FOR MY COMPANY", "WORDS ONLY", "RUPEES", "PAISA", "THANK YOU", "AUTHORIZED SIGNATORY"]
                if any(ht in raw_upper for ht in hard_terminals):
                    break
                continue
            stripped = m['raw'].strip()
            if not stripped or m['is_sep'] or "PAGE BREAK" in stripped:
                continue
            
            # --- Smart Descriptive Continuity ---
            is_summary_frag = any(rk in raw_upper for rk in ["RUPEES", "TOTAL", "SUMMARY", "THOUSAND", "LAKH", "HUNDRED", "ONLY", "PAISA", "CGST", "SGST"])
            is_continuation = last_item is not None and not has_dec and not m['has_num'] and len(stripped) > 2 and not is_summary_frag
            
            if is_continuation:
                target_key = None
                for k in ["DESC", "NAME", "PRODUCT", "ITEM", "PARTICULAR", "DETAIL"]:
                    target_key = next((c['label'] for c in current_cols if k in c['label'].upper()), None)
                    if target_key: break
                if not target_key and current_cols: target_key = current_cols[0]['label']
                if target_key:
                    last_item[target_key] = (last_item.get(target_key, "") + " " + stripped).strip()
                continue

            # 2. Heuristic Footer Rejection
            if not has_dec:
                if len(m['tokens']) <= 2 or (m['has_num'] and len(m['tokens']) <= 3): continue
            
            # 3. Keyword Rejection
            if any(rk in raw_upper for rk in self.rejection_kws) and not (m['has_num'] and len(m['tokens']) > 10): continue

            # --- Multi-page Header Suppression ---
            if "PAGE" in raw_upper and "BREAK" in raw_upper: continue
            is_header_repeat = any(c['label'].upper() in raw_upper for c in current_cols) and not has_dec
            if is_header_repeat and i > table_start_idx + 3: continue

            if not is_summary_line:
                # Hard-Stop Protocol
                terminal_markers = ["TOTAL", "SUMMARY", "TAX =", "TERMS AND", "DECLARATION", "FOR MY COMPANY", "WORDS ONLY", "PAISA", "E & O.E", "E.O.E"]
                if any(tm in raw_upper for tm in terminal_markers) and len(raw_upper) < 200:
                    break

                # Capture row data into specific pillars
                row_data = {}
                item_found = False
                
                for idx_c, c in enumerate(current_cols):
                    lbl_up = c['label'].upper()
                    c_text_parts = []
                    for t in m['tokens']:
                        # Token's visual span
                        t_start, t_end = t.start(), t.end()
                        c_start, c_end = c['start'], c['end']
                        
                        # Calculate overlap
                        overlap_start = max(t_start, c_start)
                        overlap_end = min(t_end, c_end)
                        overlap_len = max(0, overlap_end - overlap_start)
                        
                        # Logic: If token is mostly inside this column, or column is mostly inside this token
                        # we take the token.
                        if overlap_len > 0:
                            t_len = t_end - t_start
                            # 60% overlap threshold or absolute overlap of at least 2 chars
                            if (overlap_len / t_len >= 0.6) or (overlap_len >= 2):
                                # Check if it's already assigned to a previous column to avoid duplicates
                                # (unless it's a very wide token that spans both)
                                c_text_parts.append(t.group(0).strip())
                    
                    if not c_text_parts: continue
                    c_text_raw = " ".join(c_text_parts).strip()

                    # Surgical Sanitization
                    summary_markers = ["TOTAL", "RUPEES", "DECLARATION", "====", "----", "RS.", "CGST", "SGST", "IGST", "TAX"]
                    for tm in summary_markers:
                        if tm in c_text_raw.upper() and not any(k in lbl_up for k in ["DESC", "ITEM", "NAME"]):
                             c_text_raw = re.split(re.escape(tm), c_text_raw, flags=re.I)[0].strip()

                    if not c_text_raw or any(rk in c_text_raw.upper() for rk in ["THOUSAND", "LAKH", "ONLY", "PAISA", "HUNDRED"]):
                         continue

                    # Feature-Specific Extraction Logic
                    if any(k in lbl_up for k in ["AMOUNT", "RATE", "PRICE", "TAX", "QTY", "UNIT COST", "DISC", "VALUE", "HSN", "SAC", "CODE"]):
                         sub_tokens = []
                         # Attempt to split if the token contains both letters and numbers (OCR fusion)
                         for part in c_text_parts:
                             sub_tokens.extend(re.split(r'(?<=[a-zA-Z])(?=\d)|(?<=\d)(?=[a-zA-Z])|\s{2,}', part))
                         
                         # Find the best numeric candidate (preferring one with decimal for Amount/Rate)
                         num_candidates = [s for s in sub_tokens if bool(re.search(r'\d', s))]
                         if num_candidates:
                             # For monetary columns, pick the one that looks like a price (has decimal/comma)
                             monetary = [s for s in num_candidates if bool(re.search(r'[,\.]\d{2}\b', s))]
                             if monetary:
                                 row_data[c['label']] = monetary[-1]
                             else:
                                 row_data[c['label']] = num_candidates[-1] if "AMOUNT" in lbl_up or "PRICE" in lbl_up else num_candidates[0]
                             item_found = True
                         else:
                             row_data[c['label']] = c_text_raw
                    else:
                        row_data[c['label']] = c_text_raw
                        item_found = True

                # Identification: Does this row start a new transaction?
                num_count = sum(1 for t in m['tokens'] if bool(re.search(r'\d', t.group(0))))
                
                starts_with_sr = False
                if current_cols and current_cols[0]['label'] in row_data:
                    sr_val = str(row_data[current_cols[0]['label']])
                    # SR usually is a small number at the start
                    if re.match(r'^[0-9SOIGB]+$', sr_val) and len(sr_val) <= 4: starts_with_sr = True

                # A line item usually has a decimal number or at least 2 numbers (Qty + Rate)
                is_main_item = (starts_with_sr or (has_dec and num_count >= 1) or num_count >= 3)
                
                if is_main_item:
                    # Final noise filter
                    if len(row_data) < 2 and not starts_with_sr:
                        item_found = False
                    else:
                        all_items.append(row_data)
                        last_item = row_data
                elif last_item is not None and item_found and len(stripped) > 3:
                    # Append orphan text to the last item
                    for col_lbl, col_val in row_data.items():
                        if col_val:
                            if col_lbl in last_item:
                                if not any(char.isdigit() for char in str(col_val)):
                                    last_item[col_lbl] = (str(last_item[col_lbl]) + " " + str(col_val)).strip()
                            else:
                                last_item[col_lbl] = col_val




        # 5. Rhythmic Validation & Metadata Propagation (Robot with a Ruler)
        if not all_items: return []
        
        # Count numerical presence for each column label
        col_counts = {}
        for item in all_items:
            for k, v in item.items():
                if k in global_info: continue
                if any(char.isdigit() for char in str(v)):
                    col_counts[k] = col_counts.get(k, 0) + 1
        
        if not col_counts: 
            # Propagate even if no numeric rhythm found
            return [{**global_info, **item} for item in all_items]
            
        max_rhythm = max(col_counts.values())
        
        final_list = []
        for item in all_items:
             reliable_hits = sum(1 for k, v in item.items() if k in col_counts and (col_counts[k] >= (max_rhythm * 0.2)) and any(c.isdigit() for c in str(v)))
             if reliable_hits >= 1:
                 # Flatten Global Info into each row
                 merged_item = {**global_info, **item}
                 final_list.append(merged_item)
        
        return final_list if final_list else [{**global_info, **item} for item in all_items]


    def save_to_excel(self, items, output_path):
        if not items: return None
        df = pd.DataFrame(items)
        df.to_excel(output_path, index=False)
        return output_path

