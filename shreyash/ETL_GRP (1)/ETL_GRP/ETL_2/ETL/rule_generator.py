#rule_generator.py

import re
import pandas as pd
import os

class RuleGenerator:
    _nlp_model = None
    _doc_qa_pipe = None

    def __init__(self, text_content):
        self.text_content = text_content
        self.lines = [line.rstrip() for line in text_content.split('\n')]
        self.rules = []
        self.rule_counter = 1

    def _get_line_metrics(self, line):
        """Analyze the geometric and character rhythm of a line."""
        stripped = line.strip()
        if not stripped: 
            return {'tokens': 0, 'has_num': False, 'density': 0, 'is_sep': False, 'raw': line}
        
        tokens = re.findall(r'\S+(?:\s{1,3}\S+)*', stripped)
        has_num = bool(re.search(r'[\d,]+\.\d{1,4}|\b\d{2,}\b', stripped))
        is_sep = bool(re.fullmatch(r'[\s=\-_*#~]+', stripped or ' '))
        density = len(stripped) / len(line) if len(line) > 0 else 0
        
        return {
            'tokens': len(tokens),
            'has_num': has_num,
            'density': density,
            'is_sep': is_sep,
            'raw': line
        }

    def segment(self):
        """Identify the global Body (Table) region using cluster density and keyword weighting."""
        metrics = [self._get_line_metrics(l) for l in self.lines]
        
        h_end = 0
        max_score = -1
        
        # Keywords that strongly indicate a table header
        header_kws = ["ITEM", "DESC", "PARTICULAR", "QTY", "QUANTITY", "RATE", "PRICE", "AMOUNT", "HSN", "SAC", "VAT", "GST", "TAX", "UNIT", "NET"]
        
        for i, m in enumerate(metrics):
            raw_up = m['raw'].upper()
            kw_match_count = sum(1 for kw in header_kws if kw in raw_up)
            
            # If we find a line with 2+ header keywords, it's almost certainly the header
            if kw_match_count >= 2 and not m['has_num']:
                h_end = i
                break
                
            if not m['has_num'] and m['tokens'] >= 1:
                score = m['tokens'] + (kw_match_count * 2) # Heavily weigh keyword matches
                if score > max_score:
                    max_score = score
                    h_end = i

        f_start = len(metrics) - 1
        terminal_kws = ["GRAND TOTAL", "NET TOTAL", "INVOICE TOTAL", "ORDER TOTAL", "REPORT TOTAL", "DIVISION 01 TOTAL", "VENDOR 01-CONT TOTAL", "NET ORDER", "NET RETURN", "TAXABLE AMOUNT"]
        
        for i in range(len(metrics) - 1, h_end, -1):
            m = metrics[i]
            if any(tk in m['raw'].upper() for tk in terminal_kws):
                f_start = i
                break
            if m['tokens'] >= 3 and len(m['raw'].strip()) < 35 and m['has_num'] and i > len(metrics) - 10:
                f_start = i
                break

        return h_end, f_start

    def clean_extract(self, text, offset):
        match = re.search(r'[A-Za-z0-9₹#\(\)]', text)
        if not match: return None, 0, 0
        rel_start = match.start()
        trimmed = text[rel_start:].rstrip(" :-|_|/|\\|•|@|=|\\|;|.,₹")
        val = trimmed.strip()
        if len(val) < 2: return None, 0, 0
        return val, offset + rel_start, offset + rel_start + len(val)

    def generate_rules(self):
        self.rules = []
        h_end, f_start = self.segment()
        
        # 1. Structural Boundaries
        self.add_rule("STRUCTURE", "Line Item Start", str(h_end + 1), h_end, 0, 0, 0, 0, 0)
        self.add_rule("STRUCTURE", "Footer Start", str(f_start + 1), f_start, 0, 0, 0, 0, 0)
        
        # Metadata Extraction (Focusing on UNIQUE IDs only)
        meta_patterns = [
            ("Invoice_No", r'\b(?:INVOICE|BILL|MEMO)\s*(?:NO|#|NUM|NUMBER)\b|\b(?:INVOICE|BILL|MEMO)\s*[:\-]', r'((?!\d{2,4}[\/\-]\d{2}[\/\-]\d{2,4})[A-Za-z0-9\-/]{5,25})'),
            ("Invoice_Date", r'\b(?:DATE|DATED|DATE\s+OF\s+ISSUE)\b', r'([\d\-/]{8,12}|(?:[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})|(?:\d{1,2}\s+[a-zA-Z]{3,9}\s+\d{2,4}))'),
            ("GSTIN", r'\b(?:GSTIN|VAT|TAX\s*ID|TAX\s*LD)\b', r'([0-9]{2}[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}[1-9A-Za-z]{1}Z[0-9A-Za-z]{1}|[A-Za-z0-9 \-]{10,20})'),
            ("PAN", r'\bPAN\b', r'([A-Z]{5}[0-9]{4}[A-Z]{1})'),
            ("Bank_Account", r'\b(?:ACCOUNT|ACC|A/C)\b', r'([0-9\-/]{9,22})'),
            ("IFSC", r'\bIFSC\b', r'([A-Z]{4}0[A-Z0-9]{6})'),
            ("Bank_IBAN", r'\bIBAN\b', r'([A-Z]{2}[0-9]{2}[A-Za-z0-9]{12,30})'),
        ]

        def scan_for_meta(start_line, end_line, section):
            for idx in range(start_line, end_line):
                if idx >= len(self.lines): break
                line_text = self.lines[idx]
                for field, h_regex, v_regex in meta_patterns:
                    match = re.search(h_regex, line_text, re.I)
                    if match:
                        header_end = match.end()
                        # Strictly look at the remainder of the SAME line first
                        suffix = line_text[header_end:].strip()
                        
                        # Cleanup delimiter and spurious label noise
                        suffix = re.sub(r'^(?:[\s\.:\-\#]|NO|NUM|NUMBER|DATE|OF|ISSUE)+', '', suffix, flags=re.I).strip()
                        
                        val_match = re.search(v_regex, suffix, re.I)
                        if val_match:
                             val = val_match.group(1)
                             if any(n in val.upper() for n in ["ORIGINAL", "DUPLICATE", "TRIPLICATE", "RECIPIENT", "TRANSPORTER", "SUPPLIER"]):
                                 continue
                             if field == "Invoice_No":
                                 if re.search(r'^\d{1,2}[\/\-\.\s]{1,2}(?:[a-zA-Z]{3,9}|\d{1,2})[\/\-\.\s]{1,2}\d{2,4}$', val.strip()):
                                     continue
                             self.add_rule(section, field, val, idx, match.start(), match.end(), header_end + val_match.start(), header_end + val_match.end(), 0)
                             continue

                        # If not on same line, look at the line strictly below
                        if idx + 1 < len(self.lines):
                             next_line = self.lines[idx+1].strip()
                             # Clean next line if it starts with noise
                             next_line = re.sub(r'^(?:[\s\.:\-\#]|NO|NUM|NUMBER|DATE|OF|ISSUE)+', '', next_line, flags=re.I).strip()
                             val_match = re.search(v_regex, next_line, re.I)
                             if val_match:
                                 val = val_match.group(1)
                                 if any(n in val.upper() for n in ["ORIGINAL", "DUPLICATE", "TRIPLICATE", "RECIPIENT", "TRANSPORTER", "SUPPLIER"]):
                                     continue
                                 if field == "Invoice_No":
                                     if re.search(r'^\d{1,2}[\/\-\.\s]{1,2}(?:[a-zA-Z]{3,9}|\d{1,2})[\/\-\.\s]{1,2}\d{2,4}$', val.strip()):
                                         continue
                                 self.add_rule(section, field, val, idx+1, 0, 0, val_match.start(), val_match.end(), 1)
                                 continue

        scan_for_meta(0, h_end, "HEADER")
        scan_for_meta(f_start, len(self.lines), "FOOTER")

        # 3. Dynamic Lattice Mapping (COLUMNS ONLY)
        h_line = self.lines[h_end]
        # Use regex to find tokens with possible spaces (multi-word headers like "Item Desc")
        h_tokens = [t for t in re.finditer(r'\S+(?:\s\S+)*', h_line)]
        for i, ht in enumerate(h_tokens):
            label = ht.group(0).strip()
            if len(label) < 2: continue
            if label.upper() in ["PAGE", "INV", "NO.", "=====", "TERMS", "WORDS", "ONLY", "_____", "-----", "DECLARATION", "(₹)", "DETAILS"]: continue
            prev_e = h_tokens[i-1].end() if i > 0 else 0
            curr_s = ht.start()
            c_s = int((prev_e + curr_s) / 2) if i > 0 else 0
            curr_e = ht.end()
            next_s = h_tokens[i+1].start() if i < len(h_tokens) - 1 else 999
            c_e = int((curr_e + next_s) / 2) if i < len(h_tokens) - 1 else 999
            self.add_rule("COLUMNS", label, label, h_end, curr_s, curr_e, c_s, c_e, 0)
        
        # 4. Document Topology Markers
        self.add_rule("TOPOLOGY", "HEADER", str(h_end + 1), 0, 0, 0, 0, h_end, 0)
        self.add_rule("TOPOLOGY", "TABLE", str(f_start + 1), h_end, f_start, 0, 0, 0, 0)
        self.add_rule("TOPOLOGY", "FOOTER", str(len(self.lines)), f_start, len(self.lines), 0, 0, 0, 0)

        return self.rules

    def add_rule(self, section, field, val, line, ks, ke, bs, be, multi):
        field_name = field.strip()
        if not field_name or len(field_name) < 2: return
        if section not in ["STRUCTURE", "TABLE_START", "COLUMNS", "TOPOLOGY"]:
            for r in self.rules:
                if r['Row'] == line + 1 and r['Column Start'] == bs: return
                if r['Field Name'] == field_name and r['Sample Text'] == val: return
        v_str = str(val).replace("\n", " ").strip()
        dtype = "Numeric" if re.match(r'^[\d\.,\-\/ ]+$', v_str) else "Alphanumeric"
        self.rules.append({
            "Section": section, "Rule ID": f"{section[0]}{self.rule_counter:03}",
            "Rule type": section, "Field Name": field_name, "Sample Text": v_str,
            "Field Datatype": dtype, "Multiline": multi, 
            "Keyword Start": ks, "Keyword End": ke, "Column Start": bs, "Column End": be, "Row": line + 1,
            "Field Size_max": 4000, "Label Left": field
        })
        self.rule_counter += 1
