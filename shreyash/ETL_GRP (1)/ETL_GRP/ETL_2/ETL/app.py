import streamlit as st
import os
import tempfile
import io
import pandas as pd
import datetime
from bill_to_text import BillConverter
from rule_generator import RuleGenerator
from main_extractor import MainExtractor

# Ensure output directories exist relative to project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PARENT_DIR, "output")
TXT_DIR = os.path.join(OUTPUT_DIR, "txt")
RULES_DIR = os.path.join(OUTPUT_DIR, "rules")

os.makedirs(TXT_DIR, exist_ok=True)
os.makedirs(RULES_DIR, exist_ok=True)
XLSX_DIR = os.path.join(OUTPUT_DIR, "xlsx")
os.makedirs(XLSX_DIR, exist_ok=True)

# Page Configuration
st.set_page_config(
    page_title="Intelligent Bill ETL & Rule Engine",
    page_icon="📑",
    layout="wide",
)

# Custom CSS for Premium Look
st.markdown("""
    <style>
    .main {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.2em;
        background: linear-gradient(45deg, #238636, #2ea043);
        color: white;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
    }
    .preview-box {
        background-color: #161b22;
        color: #8b949e;
        padding: 20px;
        border-radius: 8px;
        font-family: 'Fira Code', 'Courier New', monospace;
        white-space: pre;
        overflow-x: auto;
        border: 1px solid #30363d;
        font-size: 0.9rem;
    }
    .status-card {
        background-color: #21262d;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #238636;
        margin-bottom: 20px;
    }
    h1, h2, h3 {
        color: #58a6ff !important;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def get_engines():
    """Load and cache all heavy AI models once."""
    st.info("🔄 Initializing AI Engines (LayoutLM, EasyOCR, SpaCy)... This may take a minute on first run.")
    try:
        converter = BillConverter()
        # We'll initialize Generator/Extractor with empty text just to load models
        generator = RuleGenerator("")
        extractor = MainExtractor("")
        return converter, generator, extractor
    except Exception as e:
        st.error(f"Error loading models: {e}")
        return None, None, None

def main():
    st.title("📑 Intelligent Document ETL & Rule Engine")
    st.markdown("##### Enterprise-grade Header/Body Extraction for Complex Bills & Multi-format Invoices")
    
    # Pre-load engines
    converter_engine, generator_engine, extractor_engine = get_engines()
    
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📁 Document Input")
        uploaded_files = st.file_uploader("Upload complex bills (PDF/Images)", type=["pdf", "jpg", "png", "jpeg"], accept_multiple_files=True)
        
        if uploaded_files:
            st.info(f"Loaded {len(uploaded_files)} document(s). Ready for Processing.")
            
            if st.button("🚀 Process & Generate Rules"):
                if not converter_engine:
                    st.error("AI Engines not loaded correctly. Please check logs.")
                    return

                progress_bar = st.progress(0)
                all_line_items = []
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    with st.status(f"Processing: {uploaded_file.name}...", expanded=False) as status:
                        try:
                            # 1. Save and Convert
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_path = tmp_file.name
                            
                            # Use converter_engine for logic
                            text_result = converter_engine.convert(tmp_path)
                            
                            # 2. Save Text Output
                            base_name = os.path.splitext(uploaded_file.name)[0]
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            txt_filename = f"{base_name}_{timestamp}.txt"
                            txt_path = os.path.join(TXT_DIR, txt_filename)
                            with open(txt_path, "w", encoding="utf-8") as f:
                                f.write(text_result)
                            
                            # 3. New Engines per Bill (Lightweight since models are class-cached)
                            generator = RuleGenerator(text_result)
                            extractor = MainExtractor(text_result)
                            
                            rules = generator.generate_rules()
                            line_items = extractor.extract_line_items()
                            all_line_items.extend(line_items)
                            
                            # 4. Save individual rules and items by unique input name
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            rule_filename = f"{base_name}_{timestamp}_rules.xlsx"
                            item_filename = f"{base_name}_{timestamp}_items.xlsx"
                            
                            rule_path = os.path.join(RULES_DIR, rule_filename)
                            item_path = os.path.join(XLSX_DIR, item_filename)
                            
                            if rules:
                                df_rules = pd.DataFrame(rules)
                                df_rules.to_excel(rule_path, index=False)
                            else:
                                st.warning(f"No extraction rules discovered for {uploaded_file.name}")
                                
                            if line_items:
                                df_items = pd.DataFrame(line_items)
                                df_items.to_excel(item_path, index=False)

                            # 5. Prepare Session State for Review (pointing to the most recent specific files)
                            st.session_state['last_result'] = {
                                    'text': text_result,
                                    'name': uploaded_file.name,
                                    'rules': rules,
                                    'line_items': line_items,
                                    'rule_path': rule_path,
                                    'item_path': item_path
                            }
                            status.update(label=f"✅ {uploaded_file.name} (Stored: {item_filename})", state="complete")
                            
                            os.unlink(tmp_path)
                        except Exception as e:
                            st.error(f"Critical Error processing {uploaded_file.name}: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
                    
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                # 6. Save combined main.xlsx for the whole batch if desired, but prioritize individual files
                if all_line_items:
                    main_df = pd.DataFrame(all_line_items)
                    main_path = os.path.join(XLSX_DIR, f"COMBINED_BATCH_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
                    main_df.to_excel(main_path, index=False)
                    st.session_state['main_path'] = main_path
                    st.session_state['all_line_items'] = all_line_items
                    st.success(f"Processing Complete! Files stored in: \n\n - **Text**: `{TXT_DIR}` \n - **Rules**: `{RULES_DIR}` \n - **XLSX**: `{XLSX_DIR}`")
                else:
                    st.warning("No line items were extracted from the uploaded document(s).")

    with col2:
        st.subheader("🖥️ Workspace Review")
        if 'last_result' in st.session_state or (os.path.exists(TXT_DIR) and os.listdir(TXT_DIR)):
            tab1, tab2, tab3 = st.tabs([".txt Preview", "Rules (.xlsx)", "Items (.xlsx)"])
            
            with tab1:
                st.markdown("### 📄 Extracted Text (.txt)")
                txt_files = sorted([f for f in os.listdir(TXT_DIR) if f.endswith(".txt")], reverse=True)
                if txt_files:
                    target_file = txt_files[0]
                    with open(os.path.join(TXT_DIR, target_file), 'r', encoding='utf-8') as f:
                        content = f.read()
                    st.markdown(f'<div class="preview-box">{content}</div>', unsafe_allow_html=True)
                    st.info(f"Viewing Latest Extract: `{target_file}`")
                else:
                    st.info("No .txt files generated yet.")
            
            with tab2:
                st.markdown("### 📊 Document Rules (.xlsx)")
                rule_files = sorted([f for f in os.listdir(RULES_DIR) if f.endswith(".xlsx")], reverse=True)
                if rule_files:
                    rule_file = os.path.join(RULES_DIR, rule_files[0])
                    df_rules = pd.read_excel(rule_file)
                    st.dataframe(df_rules, use_container_width=True)
                    with open(rule_file, 'rb') as f:
                        st.download_button(f"📥 Download {rule_files[0]}", f, file_name=rule_files[0])
                else:
                    st.info("No rule files generated yet.")

            with tab3:
                st.markdown("### 🛒 Extracted Table Items (.xlsx)")
                item_files = sorted([f for f in os.listdir(XLSX_DIR) if f.endswith(".xlsx") and "COMBINED" not in f], reverse=True)
                if item_files:
                    item_file = os.path.join(XLSX_DIR, item_files[0])
                    df_items = pd.read_excel(item_file)
                    st.dataframe(df_items, use_container_width=True)
                    with open(item_file, 'rb') as f:
                        st.download_button(f"📥 Download {item_files[0]}", f, file_name=item_files[0])
                else:
                    st.info("No item files generated yet.")
        else:
            st.info("Upload and process documents to see individual outputs here.")

    # Footer Persistence Info
    st.markdown("---")
    st.markdown(f"**Storage Sync**: Active | **Output Root**: `{os.path.abspath(OUTPUT_DIR)}`")

if __name__ == "__main__":
    with st.sidebar:
        st.header("⚡ System Architecture")
        try:
            import spacy
            st.success("🧠 LayoutLM Emulation: Active")
            st.caption("NER Model: en_core_web_sm")
        except:
            st.warning("🧠 LayoutLM Emulation: Limited")
        
        st.markdown("---")
        st.subheader("📂 Local Output History")
        txt_files = os.listdir(TXT_DIR) if os.path.exists(TXT_DIR) else []
        rule_files = os.listdir(RULES_DIR) if os.path.exists(RULES_DIR) else []
        
        st.metric("TXT Generated", len(txt_files))
        st.metric("Rules Generated", len(rule_files))
        xlsx_files = os.listdir(XLSX_DIR) if os.path.exists(XLSX_DIR) else []
        st.metric("XLSX Generated", len(xlsx_files))
        
        if st.button("🗑️ Clear Local Output"):
            locked_files = []
            for d in [TXT_DIR, RULES_DIR, XLSX_DIR]:
                if os.path.exists(d):
                    for f in os.listdir(d):
                        try:
                            os.remove(os.path.join(d, f))
                        except Exception:
                            locked_files.append(f)
            
            if locked_files:
                st.warning(f"Note: {len(locked_files)} files are currently locked by another process (e.g. Excel) and couldn't be deleted.")
            
            if 'last_result' in st.session_state: del st.session_state['last_result']
            if 'all_line_items' in st.session_state: del st.session_state['all_line_items']
            st.rerun()

    main()
