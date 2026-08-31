import os
import sqlite3
import pandas as pd
import streamlit as st

DB_FILE = "custom_college_events.db"


def init_db():
    """Create the SQLite database table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department TEXT NOT NULL,
            year TEXT NOT NULL,
            event_name TEXT NOT NULL,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()

st.set_page_config(page_title="College Event Data Collector", layout="wide")

st.title("🎓 College Event Dataset Creator")
st.write(
    "Fill out the form below to register. All submitted entries build your custom dataset!"
)

st.markdown("---")

# --- USER INPUT FORM ---
st.subheader("📝 Student Registration Form")

with st.form(key="user_input_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        student_id = st.text_input(
            "Student Roll / ID No.", placeholder="e.g., 21CS045"
        )
        name = st.text_input("Full Name", placeholder="e.g., Alex Mercer")
        email = st.text_input("Email Address", placeholder="e.g., alex@college.edu")

    with col2:
        department = st.selectbox(
            "Department",
            [
                "Computer Science",
                "Information Technology",
                "Electronics & Comm",
                "Mechanical",
                "Civil",
                "Biotechnology",
            ],
        )
        year = st.selectbox("Academic Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"])
        event_name = st.selectbox(
            "Select Event",
            [
                "AI & ML Workshop",
                "Web Hackathon 2026",
                "Cultural Night",
                "Paper Presentation",
                "Gaming Tournament",
            ],
        )

    submit_button = st.form_submit_button("Submit Registration")

if submit_button:
    if student_id.strip() and name.strip() and email.strip():
        # Save to SQLite
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO custom_registrations (student_id, name, email, department, year, event_name)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                student_id.strip(),
                name.strip(),
                email.strip(),
                department,
                year,
                event_name,
            ),
        )
        conn.commit()
        conn.close()

        st.success(f"✅ Registration recorded for **{name}**!")
    else:
        st.error("⚠️ Please fill out all required text fields.")

st.markdown("---")

# --- VIEW AND EXPORT DATASET ---
st.subheader("📊 Collected Custom Dataset")

conn = sqlite3.connect(DB_FILE)
df = pd.read_sql_query(
    "SELECT * FROM custom_registrations ORDER BY registration_time DESC", conn
)
conn.close()

if not df.empty:
    st.dataframe(df, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # Export as CSV
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Dataset as CSV",
            data=csv_data,
            file_name="college_event_dataset.csv",
            mime="text/csv",
        )

    with col2:
        # Show quick dataset stats
        st.write(f"**Total Records Collected:** {len(df)}")
else:
    st.info(
        "No registrations in your dataset yet. Submit the form above to start building it!"
    )
