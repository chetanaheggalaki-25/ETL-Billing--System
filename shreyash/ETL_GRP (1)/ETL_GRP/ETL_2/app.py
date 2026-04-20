import os
import shutil
from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
import sys

# Ensure ETL folder is in path
sys.path.append(os.path.join(os.getcwd(), "ETL"))

from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor

app = Flask(__name__)
CORS(app)  # Allow React frontend (port 5173) to call this API
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output/xlsx'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

converter = BillConverter()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # 1. Convert to Text
            text, word_map = converter.convert(file_path)
            
            # 2. Extract Rules & Data
            generator = RuleGenerator(text)
            rules = generator.generate_rules()
            
            extractor = MainExtractor(text, rules)
            items = extractor.extract_line_items(word_map)
            
            if not items:
                return jsonify({"error": "No data items found in this document. Please check the file format."}), 422
            
            # 3. Save to Excel
            df = pd.DataFrame(items)
            clean_name = secure_filename(filename.split('.')[0])
            output_filename = f"{clean_name}_extracted.xlsx"
            output_path = os.path.abspath(os.path.join(app.config['OUTPUT_FOLDER'], output_filename))
            df.to_excel(output_path, index=False)
            
            return jsonify({
                "message": "Extraction Successful",
                "filename": output_filename,
                "download_url": f"/download/{output_filename}",
                "preview_data": items[:3], # Send first 3 items for UI preview
                "raw_text": text,
                "rules": rules
            })
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return jsonify({"error": f"Internal Process Error: {str(e)}"}), 500

@app.route('/reprocess', methods=['POST'])
def reprocess():
    try:
        data = request.json
        text = data.get('raw_text')
        rules = data.get('rules')
        filename = data.get('filename', 'reprocessed.xlsx')

        if not text or not rules:
            return jsonify({"error": "Missing text or rules"}), 400

        extractor = MainExtractor(text, rules=rules)
        items = extractor.extract_line_items()

        if not items:
            return jsonify({"error": "No items extracted with these rules"}), 422

        df = pd.DataFrame(items)
        output_filename = f"{secure_filename(filename.split('.')[0])}_extracted.xlsx"
        output_path = os.path.abspath(os.path.join(app.config['OUTPUT_FOLDER'], output_filename))
        df.to_excel(output_path, index=False)

        return jsonify({
            "message": "Reprocessing Successful",
            "download_url": f"/download/{output_filename}",
            "preview_data": items[:3]
        })
    except Exception as e:
        print(f"  [REPROCESS ERROR] {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    print(f"  [DOWNLOAD REQUEST] Requested: {filename}")
    path = os.path.abspath(os.path.join(app.config['OUTPUT_FOLDER'], filename))
    if not os.path.exists(path):
        print(f"  [DOWNLOAD ERROR] File not found: {path}")
        return jsonify({"error": "File not found"}), 404
    print(f"  [DOWNLOAD SUCCESS] Serving: {path}")
    return send_file(
        path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    print("Aveenya ETL Server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
