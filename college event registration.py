import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "college_events_pure.db"

# --- DATABASE LOGIC ---

def init_database():
    """Initializes the database tables and populates sample event schema if empty."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            dob TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            venue TEXT NOT NULL,
            event_time TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            event_id INTEGER NOT NULL,
            registration_date TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (student_id),
            FOREIGN KEY (event_id) REFERENCES events (event_id)
        )
    ''')
    
    # Populate default master events if table is empty (Using standardized YYYY-MM-DD HH:MM format for quick comparisons)
    cursor.execute("SELECT COUNT(*) FROM events")
    if cursor.fetchone()[0] == 0:
        sample_events = [
            ("Dance Competition", "Cultural", "Main Auditorium", "2026-07-15 10:00"),
            ("Paper Presentation", "Technical", "Seminar Hall Block A", "2026-07-15 14:00"),
            ("Music Concert", "Cultural", "Open Air Theatre (OAT)", "2026-07-16 18:00"),
            ("Code Debugging", "Technical", "Lab 3, CSE Dept", "2026-07-16 11:30"),
            ("AI Hackathon", "Technical", "Main Seminar Hall", "2026-07-15 10:00") # Sample event to test same-time clash
        ]
        cursor.executemany(
            "INSERT INTO events (event_name, category, venue, event_time) VALUES (?, ?, ?, ?)", 
            sample_events
        )
        
    # Populate some default students if table is empty
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        sample_students = [
            ("STU401", "2004-05-12", "Niran J", "Computer Science"),
            ("STU402", "2005-09-21", "Sarah Connor", "Information Technology")
        ]
        cursor.executemany(
            "INSERT INTO students (student_id, dob, name, department) VALUES (?, ?, ?, ?)", 
            sample_students
        )
        
    conn.commit()
    conn.close()

def get_db_data(query, params=()):
    """Helper function to safely fetch data into a Pandas DataFrame."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# --- STREAMLIT UI CONFIG ---
st.set_page_config(page_title="College Event Portal", page_icon="🎓", layout="wide")
init_database()

st.title("🎓 College Event Database Management System")
st.markdown("---")

# --- SIDEBAR: ADD NEW STUDENT ---
st.sidebar.header("➕ Add New Student")
with st.sidebar.form(key="student_form", clear_on_submit=True):
    new_id = st.text_input("Student ID (e.g., STU403)").strip()
    new_name = st.text_input("Full Name")
    new_dob = st.date_input("Date of Birth", min_value=datetime(2000, 1, 1))
    new_dept = st.selectbox("Department", ["Computer Science", "Information Technology", "Electronics", "Mechanical", "Civil"])
    
    submit_student = st.form_submit_button("Register Student Profile")
    
    if submit_student:
        if new_id and new_name:
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO students VALUES (?, ?, ?, ?)", (new_id, str(new_dob), new_name, new_dept))
                conn.commit()
                conn.close()
                st.sidebar.success(f"Profile created for {new_name}!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.sidebar.error("Error: Student ID already exists.")
        else:
            st.sidebar.error("Please fill out all fields.")

# --- METRICS DASHBOARD ---
students_df = get_db_data("SELECT * FROM students")
events_df = get_db_data("SELECT * FROM events")
reg_df = get_db_data("SELECT * FROM registrations")

col1, col2, col3 = st.columns(3)
col1.metric("Total Profiles Verified", len(students_df))
col2.metric("Active Master Events", len(events_df))
col3.metric("Successful Bookings", len(reg_df))

st.markdown("---")

# --- MAIN INTERACTION: NEW EVENT REGISTRATION ---
st.header("🚀 Process Live Event Registration")

# Dropdown data mapping
student_options = {f"{row['student_id']} - {row['name']}": row['student_id'] for _, row in students_df.iterrows()}
event_options = {f"{row['event_name']} (📅 {row['event_time']})": row['event_id'] for _, row in events_df.iterrows()}

if student_options and event_options:
    c1, c2 = st.columns(2)
    with c1:
        selected_student_str = st.selectbox("Select Student Profile", list(student_options.keys()))
        student_id = student_options[selected_student_str]
        student_name = selected_student_str.split(" - ")[1]
    with c2:
        selected_event_str = st.selectbox("Select Target Event", list(event_options.keys()))
        event_id = event_options[selected_event_str]
        
    if st.button("Confirm & Process Registration", type="primary"):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # 1. Fetch details of the targeted event
        cursor.execute("SELECT event_name, event_time, venue FROM events WHERE event_id = ?", (int(event_id),))
        target_event = cursor.fetchone()
        target_name, target_time, target_venue = target_event
        
        # 2. Check strict duplicate registration
        cursor.execute("SELECT * FROM registrations WHERE student_id = ? AND event_id = ?", (student_id, int(event_id)))
        if cursor.fetchone():
            st.warning(f"⚠️ User Notification: {student_name} is already registered for '{target_name}'!")
        else:
            # 3. Time Complexity / Schedule Clash Verification Engine
            # Fetch timings of all events this student has already registered for
            cursor.execute('''
                SELECT e.event_name, e.event_time 
                FROM registrations r 
                JOIN events e ON r.event_id = e.event_id 
                WHERE r.student_id = ?
            ''', (student_id,))
            existing_registrations = cursor.fetchall()
            
            has_time_clash = False
            clashing_event_name = ""
            
            for registered_name, registered_time in existing_registrations:
                if registered_time == target_time:
                    has_time_clash = True
                    clashing_event_name = registered_name
                    break
            
            if has_time_clash:
                st.error(f"❌ Schedule Conflict! Cannot register for '{target_name}'. It conflicts with '{clashing_event_name}' scheduled at the exact same time ({target_time}).")
            else:
                # 4. Save entry if clean
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute("INSERT INTO registrations (student_id, event_id, registration_date) VALUES (?, ?, ?)", (student_id, int(event_id), now))
                conn.commit()
                
                # 5. Display the real-time generated acknowledgement block
                st.balloons()
                st.success("🎉 Registration Linkage Successfully Added to Pipeline!")
                
                # Beautifully styled Acknowledgement card
                st.markdown(f"""
                > ### 📄 Official Registration Acknowledgement
                > **Date Issued:** {now}  
                > 
                > Dear **{student_name}** (`{student_id}`),  
                > Your seat booking has been officially confirmed. Below are your event assignment credentials:
                > * **Assigned Event Name:** {target_name}  
                > * **Official Scheduled Timing:** {target_time}  
                > * **Allocated Campus Venue:** {target_venue}  
                > 
                > *Please preserve a screenshot of this dashboard section as your entry pass.*
                """)
        conn.close()
else:
    st.info("Add students using the sidebar to get started.")

st.markdown("---")

# --- DATA VIEWING TABS ---
st.header("📊 System Database Viewers")
tab1, tab2, tab3 = st.tabs(["Active Portal Reports", "All Registered Students", "Master Events List"])

with tab1:
    st.subheader("Live Registration Joined Streams")
    report_query = '''
        SELECT r.registration_id as [Reg ID], s.student_id as [Student ID], s.name as [Student Name], 
               e.event_name as [Event Name], e.venue as [Venue], e.event_time as [Scheduled Time], r.registration_date as [Processed At]
        FROM registrations r
        JOIN students s ON r.student_id = s.student_id
        JOIN events e ON r.event_id = e.event_id
    '''
    report_df = get_db_data(report_query)
    if not report_df.empty:
        st.dataframe(report_df, use_container_width=True, hide_index=True)
    else:
        st.info("No active event bookings discovered.")

with tab2:
    st.subheader("Verified Student Profiles")
    st.dataframe(students_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Master Event Configuration Timestamps")
    st.dataframe(events_df, use_container_width=True, hide_index=True)
