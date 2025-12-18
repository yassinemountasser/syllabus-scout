import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
from openai import OpenAI
import json
import plotly.express as px
from ics import Calendar, Event

# --- Page Config ---
st.set_page_config(
    page_title="SyllabusScout", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 THE DESIGN OVERHAUL (CSS) ---
st.markdown("""
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* BACKGROUND: Deep Cyber-Navy */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0f172a 0%, #020617 90%);
        color: #e2e8f0;
    }

    /* TITLES: Neon Gradient Text */
    h1 {
        background: -webkit-linear-gradient(45deg, #00f2ff, #00c6ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        font-size: 3rem !important;
    }
    h2, h3 {
        color: #94a3b8 !important;
        font-weight: 600;
    }

    /* CARDS: Glassmorphism Effect */
    div[data-testid="stMetric"], div.stDataFrame {
        background-color: rgba(30, 41, 59, 0.5); /* Semi-transparent slate */
        backdrop-filter: blur(10px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #00f2ff;
    }

    /* BUTTONS: Glowing Action Button */
    .stButton>button {
        background: linear-gradient(90deg, #0ea5e9 0%, #2563eb 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 0 15px rgba(14, 165, 233, 0.4);
    }
    .stButton>button:hover {
        box-shadow: 0 0 25px rgba(14, 165, 233, 0.7);
        transform: scale(1.02);
    }

    /* FILE UPLOADER: Clean styling */
    [data-testid="stFileUploader"] {
        border: 2px dashed #334155;
        border-radius: 10px;
        padding: 20px;
    }

    /* SIDEBAR styling */
    section[data-testid="stSidebar"] {
        background-color: #020617;
        border-right: 1px solid #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("Syllabus Scout ⚡")
    st.markdown("<h3 style='margin-top: -20px; font-size: 1.2rem; color: #64748b;'>AI-Powered Academic Intelligence Engine</h3>", unsafe_allow_html=True)
with col2:
    # Just a visual placeholder for "Status"
    st.metric("System Status", "🟢 Online", delta_color="normal")

st.divider()

# --- SIDEBAR & AUTH ---
# 1. Automatic Auth (If you set the secret in Streamlit Cloud)
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
    with st.sidebar:
        st.header("⚙️ Control Panel")
        # No "Success" message. Just the helpful info.
        st.info("💡 **Pro Tip:** Upload all your syllabi at once to detect cross-course conflicts.")
        st.markdown("---")

# 2. Manual Auth (If you are running locally without a secrets file)
else:
    with st.sidebar:
        st.header("⚙️ Control Panel")
        api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
        st.info("💡 **Pro Tip:** Upload all your syllabi at once to detect cross-course conflicts.")
        st.markdown("---")
        st.caption("v1.0.0 | Rutgers CS Project")

# --- LOGIC (Unchanged) ---
def extract_text_from_pdf(uploaded_file):
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        return ""

def parse_syllabus_with_ai(syllabus_text, api_key):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    
    system_instruction = """
    You are a strictly JSON-speaking assistant. 
    Extract ALL course deadlines, exams, projects, and assignments.
    
    CRITICAL INSTRUCTION:
    If an assignment is listed but has NO specific date, YOU MUST STILL INCLUDE IT. 
    Set the 'date' field to the string "TBD".

    Return a list of JSON objects with these keys: 
    - 'event': Name of the task
    - 'date': YYYY-MM-DD format OR "TBD"
    - 'type': "Exam", "Homework", "Project", or "Quiz"
    - 'weight': numeric percentage (e.g. 20 for 20%) - return 0 if unknown.
    
    Return ONLY the valid JSON list.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": syllabus_text[:15000]}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"AI Error: {e}")
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
uploaded_files = st.file_uploader("📂 Upload Course Syllabi (PDF)", type="pdf", accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 Initialize Analysis", type="primary"):
        
        scheduled_dfs = [] 
        unscheduled_dfs = []
        progress_bar = st.progress(0)
        
        with st.spinner("⚡ Neural Networks Analyzing Data..."):
            
            for i, file in enumerate(uploaded_files):
                text = extract_text_from_pdf(file)
                if not text: continue

                raw_json = parse_syllabus_with_ai(text, api_key)
                
                if raw_json:
                    try:
                        clean_json = raw_json.replace("```json", "").replace("```", "").strip()
                        data = json.loads(clean_json)
                        df = pd.DataFrame(data)
                        df['course'] = file.name.replace(".pdf", "")

                        df['date'] = df['date'].astype(str).str.strip()
                        is_tbd = (df['date'].str.upper() == "TBD") | (df['date'] == "") | (df['date'].str.lower() == "null")
                        
                        tbd_items = df[is_tbd].copy()
                        dated_items = df[~is_tbd].copy()

                        if not dated_items.empty:
                            dated_items['date'] = pd.to_datetime(dated_items['date'], errors='coerce')
                            failed_dates = dated_items[dated_items['date'].isna()]
                            if not failed_dates.empty:
                                failed_dates['date'] = "TBD"
                                tbd_items = pd.concat([tbd_items, failed_dates])
                                dated_items = dated_items.dropna(subset=['date'])
                            
                            if not dated_items.empty:
                                dated_items['date_str'] = dated_items['date'].dt.strftime('%Y-%m-%d')
                                dated_items['weight'] = pd.to_numeric(dated_items['weight'], errors='coerce').fillna(0)
                                scheduled_dfs.append(dated_items)

                        if not tbd_items.empty:
                            tbd_items['weight'] = pd.to_numeric(tbd_items['weight'], errors='coerce').fillna(0)
                            tbd_items['date'] = "TBD"
                            unscheduled_dfs.append(tbd_items)

                    except Exception as e:
                        st.error(f"Error parsing JSON for {file.name}: {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))

            # --- DISPLAY RESULTS ---
            master_scheduled = pd.concat(scheduled_dfs, ignore_index=True) if scheduled_dfs else pd.DataFrame()
            master_unscheduled = pd.concat(unscheduled_dfs, ignore_index=True) if unscheduled_dfs else pd.DataFrame()
            total_count = len(master_scheduled) + len(master_unscheduled)

            if total_count > 0:
                st.success("✅ Extraction Complete.")
                
                # 1. METRICS ROW
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Deliverables", total_count)
                col2.metric("Scheduled Events", len(master_scheduled))
                col3.metric("TBD Items", len(master_unscheduled))
                
                # Calculate 'Crunch Time' (Month with most work)
                if not master_scheduled.empty:
                    busy_month = master_scheduled['date'].dt.month_name().mode()[0]
                    col4.metric("Heaviest Month", busy_month)
                else:
                    col4.metric("Heaviest Month", "N/A")

                st.markdown("---")

                # 2. INTERACTIVE TIMELINE (New Colors)
                if not master_scheduled.empty:
                    st.subheader("📊 Workload Visualization")
                    
                    # Custom "Neon" Color Scale
                    fig = px.scatter(
                        master_scheduled, 
                        x="date", y="course", 
                        size="weight", 
                        color="type", # Colors are assigned automatically, but we customize the template
                        hover_data=["event", "weight"],
                        size_max=25,
                        template="plotly_dark",
                        title="Semester Timeline (Bubble Size = Grade Weight)"
                    )
                    
                    # Update chart styling to match the website theme
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", # Transparent background
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter", color="#e2e8f0"),
                        xaxis=dict(showgrid=True, gridcolor="#334155"),
                        yaxis=dict(showgrid=True, gridcolor="#334155")
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # 3. SPLIT VIEW (Tabs for better organization)
                st.markdown("### 📋 Detailed Breakdown")
                tab1, tab2 = st.tabs(["📅 Scheduled Tasks", "📌 TBD / Undated"])
                
                with tab1:
                    if not master_scheduled.empty:
                        # Style the dataframe with pandas styling
                        st.dataframe(
                            master_scheduled[['date_str', 'course', 'event', 'type', 'weight']],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No dated tasks found.")

                with tab2:
                    if not master_unscheduled.empty:
                        st.dataframe(
                            master_unscheduled[['course', 'event', 'type', 'weight']], 
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No undated tasks found.")

                # 4. EXPORT AREA
                if not master_scheduled.empty:
                    st.markdown("---")
                    col_dl1, col_dl2 = st.columns([2,1])
                    with col_dl1:
                        st.markdown("### 📲 Sync to Calendar")
                        st.caption("Download the .ics file to instantly add these to Google Calendar, Apple Calendar, or Outlook.")
                    with col_dl2:
                        ics_data = create_ics_file(master_scheduled)
                        st.download_button(
                            "📥 Download Calendar (.ics)", 
                            data=ics_data, 
                            file_name="semester_plan.ics", 
                            mime="text/calendar",
                            key="download-btn"
                        )
            else:
                st.warning("No data found in the uploaded syllabi.")

elif not api_key:
    st.warning("🔒 Please enter your API Key in the sidebar to unlock the engine.")