from datetime import datetime
import pandas as pd
import plotly.express as px
from sqlalchemy import text
import streamlit as st

# --- STREAMLIT UI CONFIG ---
st.set_page_config(
    page_title="College Event Portal", page_icon="🎓", layout="wide"
)

st.title("🎓 College Event Database Management System")
st.markdown("---")

# --- INSTANT DATABASE CONNECTION POOLING ---
db = st.connection("postgres", type="sql")


def get_connection():
    """Helper to acquire an active connection session from Streamlit's pool instantly."""
    return db.session


def get_db_data(query, params=None):
    """Helper function to fetch data safely using cached connection pooling."""
    return db.query(query, params=params, ttl=0)


# --- SIDEBAR: ADD NEW STUDENT ONLY ---
st.sidebar.header("➕ Add New Student")
with st.sidebar.form(key="student_form", clear_on_submit=True):
    new_id = st.text_input("Student ID (e.g., STU405)").strip()
    new_name = st.text_input("Full Name")
    new_dob = st.date_input(
        "Date of Birth",
        min_value=datetime(2001, 1, 1),
        max_value=datetime.now(),
    )
    new_dept = st.selectbox(
        "Department",
        [
            "Computer Science",
            "Information Technology",
            "Electronics",
            "Mechanical",
            "Civil",
        ],
    )

    submit_student = st.form_submit_button("Register Student Profile")

    if submit_student:
        if new_id and new_name:
            try:
                with get_connection() as conn:
                    conn.execute(
                        text(
                            "INSERT INTO students (student_id, dob, name, department) VALUES (:id, :dob, :name, :dept)"
                        ),
                        {
                            "id": new_id,
                            "dob": str(new_dob),
                            "name": new_name,
                            "dept": new_dept,
                        },
                    )
                    conn.commit()
                st.sidebar.success(f"Profile created for {new_name}!")
                st.rerun()
            except Exception as e:
                st.sidebar.error("Error: Student ID already exists or system busy.")
        else:
            st.sidebar.error("Please fill out all fields.")

# --- METRICS DASHBOARD ---
students_df = get_db_data("SELECT * FROM students;")
events_df = get_db_data("SELECT * FROM events;")
reg_df = get_db_data("SELECT * FROM registrations;")

col1, col2, col3 = st.columns(3)
col1.metric("Total Profiles Verified", len(students_df))
col2.metric("Active Master Events", len(events_df))
col3.metric("Successful Bookings", len(reg_df))

st.markdown("---")

# --- MAIN INTERACTION: NEW EVENT REGISTRATION ---
st.header("🚀 Process Live Event Registration")

student_options = {
    f"{row['student_id']} - {row['name']}": row["student_id"]
    for _, row in students_df.iterrows()
}
event_options = {
    f"{row['event_name']} (📅 {row['event_time']})": row["event_id"]
    for _, row in events_df.iterrows()
}

if student_options and event_options:
    c1, c2 = st.columns(2)
    with c1:
        selected_student_str = st.selectbox(
            "Select Student Profile", list(student_options.keys())
        )
        student_id = student_options[selected_student_str]
        student_name = selected_student_str.split(" - ")[1]
    with c2:
        selected_event_str = st.selectbox(
            "Select Target Event", list(event_options.keys())
        )
        event_id = event_options[selected_event_str]

    if st.button("Confirm & Process Registration", type="primary"):
        try:
            with get_connection() as conn:
                target_event = conn.execute(
                    text(
                        "SELECT event_name, event_time, venue FROM events WHERE event_id = :e_id"
                    ),
                    {"e_id": int(event_id)},
                ).fetchone()
                target_name, target_time, target_venue = target_event

                already_registered = conn.execute(
                    text(
                        "SELECT * FROM registrations WHERE student_id = :s_id AND event_id = :e_id"
                    ),
                    {"s_id": student_id, "e_id": int(event_id)},
                ).fetchone()

                if already_registered:
                    st.warning(
                        f"⚠️ User Notification: {student_name} is already registered for '{target_name}'!"
                    )
                else:
                    existing_registrations = conn.execute(
                        text("""
                        SELECT e.event_name, e.event_time 
                        FROM registrations r 
                        JOIN events e ON r.event_id = e.event_id 
                        WHERE r.student_id = :s_id
                    """),
                        {"s_id": student_id},
                    ).fetchall()

                    has_time_clash = False
                    clashing_event_name = ""

                    for registered_name, registered_time in existing_registrations:
                        if registered_time == target_time:
                            has_time_clash = True
                            clashing_event_name = registered_name
                            break

                    if has_time_clash:
                        st.error(
                            f"❌ Schedule Conflict! Cannot register for '{target_name}'. It conflicts with '{clashing_event_name}' scheduled at the exact same time ({target_time})."
                        )
                    else:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        conn.execute(
                            text(
                                "INSERT INTO registrations (student_id, event_id, registration_date) VALUES (:s_id, :e_id, :now)"
                            ),
                            {
                                "s_id": student_id,
                                "e_id": int(event_id),
                                "now": now,
                            },
                        )
                        conn.commit()

                        st.balloons()
                        st.success(
                            "🎉 Registration Linkage Successfully Added to Pipeline!"
                        )

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
                        st.rerun()
        except Exception as e:
            st.error(
                "⚠️ Server busy processing another booking. Please try again."
            )
else:
    st.info("Add students using the sidebar to get started.")

st.markdown("---")

# --- DATA VIEWING & VISUALIZATION TABS ---
st.header("📊 System Database & Analytics")
tab1, tab2, tab3, tab4 = st.tabs([
    "Active Portal Reports",
    "All Registered Students",
    "Master Events List",
    "Analytics Overview",
])

report_query = """
    SELECT r.registration_id as "Reg ID", s.student_id as "Student ID", s.name as "Student Name", 
           s.department as "Department", e.event_name as "Event Name", e.category as "Category", 
           e.venue as "Venue", e.event_time as "Scheduled Time", r.registration_date as "Processed At"
    FROM registrations r
    JOIN students s ON r.student_id = s.student_id
    JOIN events e ON r.event_id = e.event_id
"""
report_df = get_db_data(report_query)

with tab1:
    st.subheader("Live Registration Joined Streams")
    if not report_df.empty:
        st.dataframe(report_df, use_container_width=True, hide_index=True)

        csv_data = report_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Dataset as CSV",
            data=csv_data,
            file_name="college_registrations_dataset.csv",
            mime="text/csv",
        )
    else:
        st.info("No active event bookings discovered.")

with tab2:
    st.subheader("Verified Student Profiles")
    st.dataframe(students_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Master Event Configuration Timestamps")
    st.dataframe(events_df, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Event Participation Overview")

    if not report_df.empty:
        top_event = report_df["Event Name"].mode()[0]
        top_dept = report_df["Department"].mode()[0]

        m1, m2 = st.columns(2)
        m1.info(f"🏆 **Most Popular Event:** {top_event}")
        m2.info(f"🏛️ **Top Participating Dept:** {top_dept}")

        event_counts = report_df["Event Name"].value_counts().reset_index()
        event_counts.columns = ["Event Name", "Registrations"]

        dark_5_colors = ["#1f4e78", "#5b2c6f", "#0e6655", "#78281f", "#2c3e50"]

        fig_column = px.bar(
            event_counts,
            x="Event Name",
            y="Registrations",
            title="Total Registrations per Event",
            text="Registrations",
            color="Event Name",
            color_discrete_sequence=dark_5_colors,
        )

        fig_column.update_traces(textposition="outside")

        fig_column.update_layout(
            xaxis={"categoryorder": "total descending"},
            xaxis_title="Event Name",
            yaxis_title="Number of Students",
            showlegend=False,
            height=380,
            margin=dict(l=20, r=20, t=40, b=20),
        )

        st.plotly_chart(fig_column, use_container_width=True)

    else:
        st.info("No registration data available yet for analytics.")
