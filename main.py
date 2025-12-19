import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import google.generativeai as genai
import json
import plotly.express as px
from ics import Calendar, Event
import time

# --- Page Config ---
st.set_page_config(
    page_title="Syllabus Scout 🔎", 
    page_icon="🔎", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 VISUAL UPGRADE (CSS ONLY) ---
st.markdown("""
<style>
    /* IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    /* GLOBAL THEME */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* DARK MODE BACKGROUND - Deep Space Blue */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0f172a 0%, #020617 90%);
        color: #e2e8f0;
    }

    /* NEON TITLES */
    h1 {
        background: -webkit-linear-gradient(0deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }
    h2, h3 {
        color: #94a3b8 !important;
        font-weight: 600;
    }

    /* CARDS & METRICS - Glassmorphism */
    div[data-testid="stMetric"] {
        background-color: rgba(30, 41, 59, 0.5); /* Semi-transparent */
        backdrop-filter: blur(10px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important; /* Cyan Numbers */
    }

    /* BUTTONS - Blue Gradient */
    .stButton>button {
        background: linear-gradient(90deg, #0ea5e9 0%, #3b82f6 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.5);
        transform: translateY(-2px);
    }

    /* TABLE HEADERS */
    thead tr th:first-child { display:none }
    tbody th { display:none }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (BYOK LOGIC) ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # The Input Box
    api_key = st.text_input("Enter Google API Key", type="password")
    
    # Status Messages
    if not api_key:
        st.warning("⚠️ Key required to run.")
    else:
        st.success("Ready to scan! 🚀")

    st.divider()

    # THE INSTRUCTIONS
    with st.expander("❓ How to get a free key"):
        st.markdown("""
        1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
        2. Log in with your Google Account.
        3. Click **"Create API Key"**.
        4. Copy the key (it starts with `AIza...`).
        5. Paste it above!
        
        *Note: Using a key gives you 20 free requests per day.*
        """)
    


# --- FUNCTIONS ---

def extract_text_from_pdf(uploaded_file):
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        return ""

def parse_with_gemini(syllabus_text, api_key):
    genai.configure(api_key=api_key)
    
    # FIX: Use the stable alias.
    model = genai.GenerativeModel('gemini-flash-latest')
    
    system_prompt = """
    You are a strictly JSON-speaking data extractor.
    Extract every single due date, exam, and assignment from the text.
    
    CRITICAL INSTRUCTIONS:
    1. Extract Event Name, Date (YYYY-MM-DD), Type, and Weight (%).
    2. If NO date is listed (e.g. "Weekly Quizzes"), set date to "TBD".
    3. Return ONLY a valid JSON list. Do not write markdown blocks.
    
    Structure example:
    [
      {"event": "Midterm 1", "date": "2025-10-12", "type": "Exam", "weight": 20},
      {"event": "Final Project", "date": "TBD", "type": "Project", "weight": 30}
    ]
    """
    
    try:
        # Add a small delay to be safe (Rate Limit protection)
        time.sleep(1) 
        response = model.generate_content(system_prompt + "\n\nSYLLABUS TEXT:\n" + syllabus_text)
        return response.text
    except Exception as e:
        st.error(f"Gemini Error: {e}")
        return None

def create_ics_file(df):
    c = Calendar()
    for index, row in df.iterrows():
        try:
            e = Event()
            e.name = f"{row['event']} ({row['course']})"
            e.begin = row['date']
            e.description = f"Type: {row['type']}\nWeight: {row['weight']}%"
            e.make_all_day()
            c.events.add(e)
        except:
            continue
    return str(c)

def process_and_add_data(raw_json, source_name, scheduled_list, unscheduled_list):
    """Helper to clean JSON and append to lists"""
    if raw_json:
        try:
            # Clean up JSON (Gemini sometimes adds markdown blocks)
            clean_json = raw_json.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            df = pd.DataFrame(data)
            df['course'] = source_name

            # Normalize Columns
            df['date'] = df['date'].astype(str).str.strip()
            df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)

            # Split TBD vs Dates
            is_tbd = (df['date'].str.upper() == "TBD") | (df['date'] == "") | (df['date'].str.lower() == "null")
            
            tbd_items = df[is_tbd].copy()
            dated_items = df[~is_tbd].copy()

            # Process Dates
            if not dated_items.empty:
                dated_items['date'] = pd.to_datetime(dated_items['date'], errors='coerce')
                dated_items = dated_items.dropna(subset=['date'])
                if not dated_items.empty:
                    dated_items['date_str'] = dated_items['date'].dt.strftime('%Y-%m-%d')
                    scheduled_list.append(dated_items)

            # Process TBD
            if not tbd_items.empty:
                tbd_items['date'] = "TBD"
                unscheduled_list.append(tbd_items)
        except Exception as e:
            st.error(f"Error parsing data from {source_name}: {e}")

# --- MAIN APP ---
st.title("Syllabus Scout 🔎")
st.markdown("**The Intelligent Syllabus Command Center**")

# Two Columns for Input
col_pdf, col_text = st.columns(2)

with col_pdf:
    uploaded_files = st.file_uploader("📂 Upload Syllabi (PDF)", type="pdf", accept_multiple_files=True)

with col_text:
    manual_text = st.text_area("📝 Paste Text Directly", height=150, help="Copy content from a syllabus and paste it here if you don't have a PDF.")

if (uploaded_files or manual_text) and api_key:
    if st.button("🚀 Analyze Semester", type="primary"):
        
        scheduled_dfs = [] 
        unscheduled_dfs = []
        
        # Calculate total items to process for progress bar
        total_items = (len(uploaded_files) if uploaded_files else 0) + (1 if manual_text else 0)
        progress_bar = st.progress(0)
        current_step = 0

        # 1. PROCESS MANUAL TEXT
        if manual_text:
            raw_json = parse_with_gemini(manual_text, api_key)
            process_and_add_data(raw_json, "Manual Entry", scheduled_dfs, unscheduled_dfs)
            current_step += 1
            progress_bar.progress(current_step / total_items)

        # 2. PROCESS PDFS
        if uploaded_files:
            for file in uploaded_files:
                text = extract_text_from_pdf(file)
                if text:
                    raw_json = parse_with_gemini(text, api_key)
                    process_and_add_data(raw_json, file.name.replace(".pdf", ""), scheduled_dfs, unscheduled_dfs)
                
                current_step += 1
                progress_bar.progress(current_step / total_items)

        # --- RESULTS ---
        master_scheduled = pd.concat(scheduled_dfs, ignore_index=True) if scheduled_dfs else pd.DataFrame()
        master_unscheduled = pd.concat(unscheduled_dfs, ignore_index=True) if unscheduled_dfs else pd.DataFrame()

        if not master_scheduled.empty or not master_unscheduled.empty:
            st.success("Analysis Complete!")
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Events", len(master_scheduled) + len(master_unscheduled))
            col2.metric("Scheduled", len(master_scheduled))
            col3.metric("To Be Announced", len(master_unscheduled))
            
            st.divider()

            # 1. Timeline Chart (VISUALLY UPGRADED)
            if not master_scheduled.empty:
                st.subheader("📊 Workload Timeline")
                fig = px.scatter(
                    master_scheduled, x="date", y="course", 
                    size="weight", color="type",
                    hover_data=["event", "weight"],
                    size_max=30, # Bigger Bubbles
                    template="plotly_dark", # Dark Mode
                    color_discrete_sequence=px.colors.qualitative.Pastel, # Neon Colors
                    title="Semester Overview"
                )
                
                # Make the chart transparent and clean
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter", size=14),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#334155")
                )
                
                st.plotly_chart(fig, use_container_width=True)

            # 2. THE TABLES (High Visibility)
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.subheader("✅ Scheduled Items")
                if not master_scheduled.empty:
                    st.dataframe(
                        master_scheduled[['date_str', 'course', 'event', 'weight']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No dated items found.")

            with col_right:
                st.subheader("📌 TBD Items")
                if not master_unscheduled.empty:
                    st.dataframe(
                        master_unscheduled[['course', 'event', 'weight']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No TBD items found.")
            
            # 3. Calendar Export
            if not master_scheduled.empty:
                st.divider()
                ics_data = create_ics_file(master_scheduled)
                st.download_button(
                    "📥 Download Calendar (.ics)", 
                    data=ics_data, 
                    file_name="semester.ics", 
                    mime="text/calendar"
                )
        else:
            st.warning("No data found. The AI couldn't find assignments in the text provided.")

elif not api_key:
    st.warning("Please enter your Gemini API Key in the sidebar on the top-left corner.")