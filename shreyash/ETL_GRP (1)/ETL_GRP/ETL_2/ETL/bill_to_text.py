import pdfplumber
import os
import sys
import re
import io
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
import threading

# Global lock to prevent concurrent OCR engine calls which cause internal crashes
ocr_lock = threading.Lock()

class BillConverter:
    def __init__(self, char_width=6, char_height=12):
        self.char_width = char_width
        self.char_height = char_height
        # Unified OCR Engine (PaddleOCR) - Optimized for high-precision spatial detection
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

    def pdf_to_text(self, pdf_path):
        output_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                chars = page.chars
                if not chars: continue
                
                # Group characters into lines based on their 'top' position
                lines = {}
                line_tolerance = 2
                for char in chars:
                    top = char['top']
                    found_line = next((lt for lt in lines.keys() if abs(lt - top) < line_tolerance), None)
                    if found_line is not None: lines[found_line].append(char)
                    else: lines[top] = [char]
                
                sorted_tops = sorted(lines.keys())
                min_x0_global = min(c['x0'] for c in chars)
                avg_char_width = sum(c['width'] for c in chars) / len(chars) if chars else 5
                grid_scale = avg_char_width * 0.8
                
                for top in sorted_tops:
                    line_chars = sorted(lines[top], key=lambda x: x['x0'])
                    words = []
                    if line_chars:
                        curr_word = {'text': line_chars[0]['text'], 'x0': line_chars[0]['x0'], 'x1': line_chars[0]['x1']}
                        for i in range(1, len(line_chars)):
                            c = line_chars[i]
                            if c['x0'] - curr_word['x1'] < avg_char_width * 0.4:
                                curr_word['text'] += c['text']
                                curr_word['x1'] = c['x1']
                            else:
                                words.append(curr_word)
                                curr_word = {'text': c['text'], 'x0': c['x0'], 'x1': c['x1']}
                        words.append(curr_word)
                    
                    line_str = ""
                    for w in words:
                        target_pos = int((w['x0'] - min_x0_global) / grid_scale)
                        if target_pos > len(line_str):
                            line_str += " " * (target_pos - len(line_str))
                        elif len(line_str) > 0 and line_str[-1] != " ":
                            line_str += " "
                        line_str += w['text']
                    output_text += line_str.rstrip() + "\n"
                output_text += "\n" + "="*80 + "\n\n"
        return output_text

    def _process_ocr_result(self, ocr_results, page_width, page_height, grid_width=160):
        """
        Uses a Vertical-Bucket Overlap algorithm to force words onto correct rows
        and absolute coordinate mapping for horizontal alignment.
        """
        if not ocr_results or not ocr_results[0]:
            return ""
        
        # 1. Global Scaling
        page_data = ocr_results[0]
        # Use a higher density grid for better column precision
        scale_x = grid_width / page_width
        block_heights = [item[0][2][1] - item[0][0][1] for item in page_data]
        # Dynamically calculate line height for better bucketing
        line_height_step = sum(block_heights) / len(block_heights) if block_heights else 30
        
        # 2. Vertical Bucketing
        blocks = []
        for item in page_data:
            box = item[0]
            text = item[1][0]
            blocks.append({
                'text': text, 
                'box': box, 
                'y_top': box[0][1], 
                'y_bottom': box[2][1], 
                'x': box[0][0],
                'x_end': box[1][0]
            })
        blocks.sort(key=lambda b: b['y_top'])
        
        lines = []
        for block in blocks:
            placed = False
            for line in lines:
                # Calculate average height and overlap
                line_y_top = sum(b['y_top'] for b in line) / len(line)
                line_y_bottom = sum(b['y_bottom'] for b in line) / len(line)
                
                overlap = min(block['y_bottom'], line_y_bottom) - max(block['y_top'], line_y_top)
                h = max(block['y_bottom'] - block['y_top'], line_y_bottom - line_y_top, 1)
                
                # If overlapped by more than 50%, or within a tight tolerance, merge rows
                if overlap / h > 0.5 or abs(block['y_top'] - line_y_top) < (line_height_step * 0.3):
                    line.append(block)
                    placed = True
                    break
            if not placed:
                lines.append([block])
        
        # 3. Sort lines by appearance
        lines.sort(key=lambda l: sum(b['y_top'] for b in l) / len(l))
        
        # 4. Initialize High-Density Character Canvas
        # Increase grid size for wider bills
        grid = [[" " for _ in range(grid_width + 120)] for _ in range(len(lines) * 2 + 100)]
        last_y_avg = -1
        current_grid_row = 1
        
        min_x_global = min(b['x'] for b in blocks) if blocks else 0
        
        for line_group in lines:
            y_avg = sum(b['y_top'] for b in line_group) / len(line_group)
            
            # Map physical distance to empty text rows (but keep it compact)
            if last_y_avg != -1:
                gap = y_avg - last_y_avg
                num_steps = round(gap / line_height_step)
                current_grid_row += min(2, max(1, num_steps)) # Limit vertical gaps to prevent table fragmentation
            
            line_group.sort(key=lambda b: b['x'])
            for block in line_group:
                col_start = int((block['x'] - min_x_global) * scale_x)
                # Word-stitching: If characters are dense, write them as a block
                for i, char in enumerate(block['text']):
                    if current_grid_row < len(grid) and col_start + i < len(grid[current_grid_row]):
                        grid[current_grid_row][col_start + i] = char
            
            last_y_avg = y_avg
            
        # 5. Render Canvas to Text
        output_lines = []
        for row in grid:
            line_str = "".join(row).rstrip()
            if line_str:
                output_lines.append(line_str)
            
        return "\n".join(output_lines)

    def image_to_text(self, image_path):
        img = Image.open(image_path).convert('RGB')
        w, h = img.size
        with ocr_lock:
            res = self.ocr.ocr(np.array(img), cls=True)
        # Local word map for thread safety
        local_word_map = []
        if res and res[0]:
            for item in res[0]:
                box = item[0]
                text = item[1][0]
                local_word_map.append({
                    'text': text,
                    'x0': box[0][0],
                    'y0': box[0][1],
                    'x1': box[1][0],
                    'y1': box[2][1]
                })
        return self._process_ocr_result(res, w, h), local_word_map

    def convert(self, input_path):
        ext = os.path.splitext(input_path)[1].lower()
        local_word_map = []
        if ext == '.pdf':
            with pdfplumber.open(input_path) as pdf:
                has_text = any(page.extract_text() for page in pdf.pages)
            if has_text:
                # Capture word map for text-based PDF
                with pdfplumber.open(input_path) as pdf:
                    for page in pdf.pages:
                        words = page.extract_words()
                        for w in words:
                            local_word_map.append({
                                'text': w['text'],
                                'x0': w['x0'],
                                'y0': w['top'],
                                'x1': w['x1'],
                                'y1': w['bottom']
                            })
                return self.pdf_to_text(input_path), local_word_map
            else:
                try:
                    import fitz
                    doc = fitz.open(input_path)
                    output_text = ""
                    for page in doc:
                        w, h = page.rect.width * 2, page.rect.height * 2
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert('RGB')
                        with ocr_lock:
                            res = self.ocr.ocr(np.array(img), cls=True)
                        if res and res[0]:
                            for item in res[0]:
                                box = item[0]
                                text = item[1][0]
                                local_word_map.append({
                                    'text': text,
                                    'x0': box[0][0],
                                    'y0': box[0][1],
                                    'x1': box[1][0],
                                    'y1': box[2][1]
                                })
                        output_text += self._process_ocr_result(res, w, h) + "\n"
                    doc.close()
                    return output_text, local_word_map
                except Exception as e:
                    print(f"  [OCR ERROR] Unified Engine Failure: {str(e)}")
                    return "", []
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return self.image_to_text(input_path) # Already returns (text, word_map)
        raise ValueError(f"Unsupported format: {ext}")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    converter = BillConverter()
    try:
        result = converter.convert(sys.argv[1])
        with open(sys.argv[1] + ".txt", "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Converted {sys.argv[1]}")
    except Exception as e:
        print(f"Error: {e}")