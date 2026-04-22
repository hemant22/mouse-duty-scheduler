import streamlit as st
import pandas as pd
from datetime import datetime

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="Mouse Duty Scheduler",
    page_icon="🐭",
    layout="centered"
)

# ----------------------------
# Custom styling (Apple/Notion-like)
# ----------------------------
st.markdown("""
<style>
    .main > div {
        max-width: 980px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .block-container {
        padding-top: 1.5rem;
    }

    h1, h2, h3 {
        letter-spacing: -0.02em;
    }

    .top-caption {
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 1.25rem;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 1rem 1rem 0.8rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    .metric-label {
        color: #6b7280;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
    }

    .metric-value {
        color: #111827;
        font-size: 1.6rem;
        font-weight: 700;
        line-height: 1.1;
    }

    .duty-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 1rem 1rem 0.9rem 1rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .duty-title {
        font-size: 1.05rem;
        font-weight: 650;
        color: #111827;
        margin-bottom: 0.6rem;
        line-height: 1.3;
    }

    .duty-row {
        color: #374151;
        font-size: 0.94rem;
        margin-bottom: 0.2rem;
    }

    .status-pill {
        display: inline-block;
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 650;
        margin-bottom: 0.75rem;
    }

    .status-overdue {
        background: #fee2e2;
        color: #b91c1c;
    }

    .status-today {
        background: #fef3c7;
        color: #92400e;
    }

    .status-upcoming {
        background: #dcfce7;
        color: #166534;
    }

    .status-future {
        background: #e5e7eb;
        color: #4b5563;
    }

    .section-label {
        color: #6b7280;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        overflow: hidden;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🐭 Mouse Duty Scheduler")
st.markdown('<div class="top-caption">Clean dashboard for upcoming mouse duties. Backend: <b>Book.xlsx</b></div>', unsafe_allow_html=True)

# ----------------------------
# Load data
# ----------------------------
try:
    tbl = pd.read_excel("Book.xlsx")
except Exception as e:
    st.error(f"Could not read Book.xlsx: {e}")
    st.stop()

# ----------------------------
# Task ownership mapping
# ----------------------------
task_owner_map = {
    'Surgery Date': 'Chung-wei',
    'ABR Baseline 1  (day -3)': 'Kunpeng',
    'ABR Baseline 2 (day -1)': 'Kunpeng',
    'NIHL (Day 0)': 'Tinghan',
    'Exposed ABR1  (Day +1)': 'Kunpeng',
    'Exposed ABR 2  (Day +3)': 'Kunpeng',
    'Exposed ABR3 (Day +13)': 'Kunpeng',
    'Exposed ABR3  (Day +15)': 'Kunpeng',
}

id_col = 'Mouse ID'
arrival_col = 'BCM arrival Date'

# ----------------------------
# Date conversion
# ----------------------------
date_cols = [arrival_col] + list(task_owner_map.keys())
for col in date_cols:
    if col in tbl.columns:
        tbl[col] = pd.to_datetime(tbl[col], errors='coerce')

# ----------------------------
# Sidebar controls
# ----------------------------
st.sidebar.title("Filters")

people = sorted(set(task_owner_map.values()))
selected_person = st.sidebar.selectbox("Person", people)

view_mode = st.sidebar.radio(
    "View",
    ["All active", "Today only", "Upcoming window", "Include future"],
    index=0
)

days_ahead = st.sidebar.number_input("Upcoming within days", min_value=1, value=14)
mobile_view = st.sidebar.toggle("📱 Mobile card view", value=True)
show_summary = st.sidebar.toggle("Show summary cards", value=True)

# ----------------------------
# Build duty list
# ----------------------------
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

        if view_mode == "Today only" and status != "Today":
            continue
        elif view_mode == "Upcoming window" and status not in ["Today", "Upcoming"]:
            continue
        elif view_mode == "All active" and status == "Future":
            continue
        elif view_mode == "Include future":
            pass

        rows.append({
            "Status": status,
            "Person": owner,
            "Mouse ID": mouse_id,
            "Task": task_name,
            "Due Date": due_date.strftime('%m/%d/%Y'),
            "Days Left": days_left,
            "Arrival Date": arrival_str,
            "_sort_due": due_date
        })

if not rows:
    st.warning(f"No duties found for {selected_person}.")
    st.stop()

df = pd.DataFrame(rows).sort_values(by=["_sort_due", "Mouse ID", "Task"]).reset_index(drop=True)

# ----------------------------
# Summary counts
# ----------------------------
n_overdue = int((df["Status"] == "Overdue").sum())
n_today = int((df["Status"] == "Today").sum())
n_upcoming = int((df["Status"] == "Upcoming").sum())
n_total = len(df)

if show_summary:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Person</div><div class="metric-value" style="font-size:1.15rem;">{selected_person}</div></div>',
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Total duties</div><div class="metric-value">{n_total}</div></div>',
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Due today</div><div class="metric-value">{n_today}</div></div>',
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Overdue</div><div class="metric-value">{n_overdue}</div></div>',
            unsafe_allow_html=True
        )

st.markdown('<div class="section-label">Duty list</div>', unsafe_allow_html=True)

def color_status(val):
    if val == "Overdue":
        return "background-color: #fee2e2; color: #b91c1c;"
    elif val == "Today":
        return "background-color: #fef3c7; color: #92400e;"
    elif val == "Upcoming":
        return "background-color: #dcfce7; color: #166534;"
    return "background-color: #f3f4f6; color: #4b5563;"

# ----------------------------
# Mobile view (cards)
# ----------------------------
if mobile_view:
    for _, r in df.iterrows():
        if r["Status"] == "Overdue":
            status_class = "status-pill status-overdue"
            icon = "🔴"
        elif r["Status"] == "Today":
            status_class = "status-pill status-today"
            icon = "🟡"
        elif r["Status"] == "Upcoming":
            status_class = "status-pill status-upcoming"
            icon = "🟢"
        else:
            status_class = "status-pill status-future"
            icon = "⚪"

        card_html = f'''
        <div class="duty-card">
            <div class="{status_class}">{r["Status"]}</div>
            <div class="duty-title">{icon} {r["Task"]}</div>
            <div class="duty-row"><b>Mouse ID:</b> {r["Mouse ID"]}</div>
            <div class="duty-row"><b>Due Date:</b> {r["Due Date"]}</div>
            <div class="duty-row"><b>Days Left:</b> {r["Days Left"]}</div>
            <div class="duty-row"><b>Arrival Date:</b> {r["Arrival Date"]}</div>
            <div class="duty-row"><b>Owner:</b> {r["Person"]}</div>
        </div>
        '''
        st.markdown(card_html, unsafe_allow_html=True)

# ----------------------------
# Desktop/table view
# ----------------------------
else:
    display_df = df[["Status", "Mouse ID", "Task", "Due Date", "Days Left", "Arrival Date", "Person"]].copy()
    styled_df = display_df.style.map(color_status, subset=["Status"])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

# ----------------------------
# Footer actions
# ----------------------------
st.divider()
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Refresh Data", use_container_width=True):
        st.rerun()

with col2:
    st.caption(f"Last loaded: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}")
