[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://syllabus-scout.streamlit.app/)

Syllabus Scout is a Streamlit application that uses Google's Gemini AI to automatically extract due dates, exams, and assignments from course syllabi (PDFs or text) and organizes them into an interactive timeline and a downloadable calendar.

Features:

AI-Powered Extraction: Uses Google Gemini Flash to parse complex PDF text into structured JSON data.
Smart Parsing: Automatically distinguishes between "Scheduled" events (with specific dates) and "TBD" assignments.
Interactive Visualization: features a custom-styled Plotly timeline to visualize workload distribution.
Calendar Export: Generates a .ics file compatible with Google Calendar, Apple Calendar, and Outlook.

Tech Stack:

Frontend: Streamlit (Python)
AI/LLM: Google Generative AI (Gemini)
Data Processing: Pandas, PyMuPDF (Fitz)
Visualization: Plotly Express
Utilities: ICS (iCalendar)

Installation & Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/yassinemountasser/syllabus-scout.git
    cd syllabus-scout
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Run the application:
    ```bash
    streamlit run app.py
    ```

Usage:
1.  Get an API Key:
     Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and create a free API key.
2.  Launch the Website:
     Enter your API key in the sidebar.
3.  Upload:
     Upload your course syllabi (PDF) or paste the text directly.
4.  Analyze:
     Click "Analyze Semester" to generate your timeline and table.
5.  Export:
     Download the .ics file to import all due dates into your personal calendar.

Screenshots:

<img width="1440" height="665" alt="Screenshot 2025-12-19 at 6 12 03 PM" src="https://github.com/user-attachments/assets/3622f106-32aa-4c88-9796-44e86f56d0ff" />

<img width="1440" height="665" alt="Screenshot 2025-12-19 at 6 13 25 PM" src="https://github.com/user-attachments/assets/9978c99a-41ba-4436-be4f-c550a50c384f" />


<img width="1440" height="665" alt="Screenshot 2025-12-19 at 6 28 31 PM" src="https://github.com/user-attachments/assets/2702ad6f-2246-4195-85c8-15de30018ed9" />

License:

This project is open source and available under the [MIT License](LICENSE).
