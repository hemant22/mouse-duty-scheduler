import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Mouse Duty Scheduler", layout="wide")
st.title("🐭 Mouse Duty Scheduler")
st.markdown("Backend: **book.xlsx** (place it in the same folder as this app)")

# Load data (with error handling)
try:
    tbl = pd.read_excel("book.xlsx")
except Exception as e:
    st.error(f"Could not read book.xlsx: {e}")
    st.stop()

# Your task owner mapping (same as before)
task_owner_map = {
    'Surgery Date': 'Chung-wei',
    'ABR Baseline 1 Date (-3)': 'Kunpeng',
    'ABR Baseline 2 Date (-1)': 'Kunpeng',
    'NIHL Date (0)': 'Tinghan',
    'Exposed ABR1 Date (+1)': 'Kunpeng',
    'Exposed ABR 2 Date (+3)': 'Kunpeng',
    'Exposed ABR3 Date (+13)': 'Kunpeng',
    'Exposed ABR3 Date (+15)': 'Kunpeng',
}

id_col = 'Mouse ID'
arrival_col = 'BCM arrival Date'

# Convert date columns safely
date_cols = [arrival_col] + list(task_owner_map.keys())
for col in date_cols:
    if col in tbl.columns:
        tbl[col] = pd.to_datetime(tbl[col], errors='coerce')

# Sidebar filters (much nicer than MATLAB controls)
people = sorted(set(task_owner_map.values()))
selected_person = st.sidebar.selectbox("Person", people)
days_ahead = st.sidebar.number_input("Upcoming within days", min_value=1, value=14)
show_all = st.sidebar.checkbox("Show all duties (including Future)", value=False)

# Build the duty data (almost identical logic to your buildDutyData)
today = datetime.today().date()
rows = []

for _, row in tbl.iterrows():
    mouse_id = str(row.get(id_col, ''))
    arrival = row.get(arrival_col)
    arrival_str = arrival.strftime('%m/%d/%Y') if pd.notna(arrival) else ''

    for task_name, owner in task_owner_map.items():
        if owner != selected_person:
            continue
        if task_name not in tbl.columns:
            continue

        due = row.get(task_name)
        if pd.isna(due):
            continue

        due_date = due.date() if isinstance(due, pd.Timestamp) else due
        days_left = (due_date - today).days

        if days_left < 0:
            status = "Overdue"
        elif days_left == 0:
            status = "Today"
        elif days_left <= days_ahead:
            status = "Upcoming"
        else:
            status = "Future"

        if not show_all and status == "Future":
            continue

        rows.append({
            "Status": status,
            "Person": owner,
            "Mouse ID": mouse_id,
            "Task": task_name,
            "Due Date": due_date.strftime('%m/%d/%Y'),
            "Days Left": days_left,
            "Arrival Date": arrival_str
        })

if not rows:
    st.warning(f"No duties found for {selected_person}.")
else:
    df = pd.DataFrame(rows)
    # Nice colored status
    def color_status(val):
        if val == "Overdue": return "background-color: #ffcccc"
        elif val == "Today": return "background-color: #ffffcc"
        elif val == "Upcoming": return "background-color: #ccffcc"
        return ""

    styled_df = df.style.applymap(color_status, subset=["Status"])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Summary
    n_overdue = (df["Status"] == "Overdue").sum()
    n_today = (df["Status"] == "Today").sum()
    n_upcoming = (df["Status"] == "Upcoming").sum()
    st.success(f"{selected_person}: {len(df)} duties | Overdue: {n_overdue} | Today: {n_today} | Upcoming: {n_upcoming}")

# Refresh button (Streamlit auto-refreshes on interaction, but you can add manual)
if st.button("Refresh Data"):
    st.rerun()