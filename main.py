import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import google.generativeai as genai
import json
import plotly.express as px
from ics import Calendar, Event

# --- Page Config ---
st.set_page_config(
    page_title="SyllabusScout", 
    page_icon="📅", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS (Cleaned up - No more broken tables) ---
st.markdown("""
<style>
    /* Use standard Streamlit dark theme colors, just adding a background gradient */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0f172a 0%, #020617 90%);
        color: #e2e8f0;
    }
    
    /* Make metrics pop */
    div[data-testid="stMetric"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Check for secrets first, else ask user
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Google Gemini Connected")
    else:
        api_key = st.text_input("Google Gemini API Key", type="password", placeholder="AIzaSy...")
        st.caption("[Get a Free Key Here](https://aistudio.google.com/app/apikey)")
    
    st.markdown("---")
    st.info("💡 **Tip:** Gemini 1.5 Flash is excellent at reading messy document layouts.")

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
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # We use 1.5 Flash because it's fast, free, and smart
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    system_prompt = """
    You are a strictly JSON-speaking data extractor.
    Your job is to read a course syllabus and extract every single due date, exam, and assignment.

    RULES:
    1. Extract the Event Name, Date, Type (Exam, Quiz, HW, Project), and Weight (%).
    2. Date Format: YYYY-MM-DD.
    3. CRITICAL: If an assignment is listed but has NO date, set date to "TBD". Do not ignore it.
    4. Return ONLY a valid JSON list of objects. Do not write "Here is the JSON". Just the JSON.
    
    JSON Structure:
    [
      {"event": "Midterm 1", "date": "2024-10-12", "type": "Exam", "weight": 20},
      {"event": "Essay 1", "date": "TBD", "type": "Homework", "weight": 10}
    ]
    """
    
    try:
        # Gemini handles large context very well
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

# --- MAIN APP ---
st.title("SyllabusScout ⚡")
st.caption("Powered by Google Gemini 1.5 Flash")

uploaded_files = st.file_uploader("Upload Syllabi (PDF)", type="pdf", accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 Analyze Semester", type="primary"):
        
        scheduled_dfs = [] 
        unscheduled_dfs = []
        
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            text = extract_text_from_pdf(file)
            if not text: continue
            
            # Call Gemini
            raw_json = parse_with_gemini(text, api_key)
            
            if raw_json:
                try:
                    # Clean up JSON (Gemini sometimes adds markdown blocks)
                    clean_json = raw_json.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    df = pd.DataFrame(data)
                    df['course'] = file.name.replace(".pdf", "")

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
                            scheduled_dfs.append(dated_items)

                    # Process TBD
                    if not tbd_items.empty:
                        tbd_items['date'] = "TBD"
                        unscheduled_dfs.append(tbd_items)

                except Exception as e:
                    st.error(f"Error parsing {file.name}: {e}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))

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

            # 1. Timeline Chart
            if not master_scheduled.empty:
                st.subheader("📊 Workload Timeline")
                fig = px.scatter(
                    master_scheduled, x="date", y="course", 
                    size="weight", color="type",
                    hover_data=["event", "weight"],
                    size_max=25, template="plotly_dark",
                    title="Semester Overview"
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
            st.warning("No data found. The AI couldn't read the dates from this PDF.")

elif not api_key:
    st.warning("Please enter your Gemini API Key in the sidebar.")