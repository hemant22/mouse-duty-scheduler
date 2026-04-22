import streamlit as st
import pandas as pd
import json
import base64
import requests
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
    .block-container { padding-top: 1.5rem; }
    h1, h2, h3 { letter-spacing: -0.02em; }
    .top-caption { color: #6b7280; font-size: 0.95rem; margin-bottom: 1.25rem; }
    .metric-card {
        background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 18px; padding: 1rem 1rem 0.8rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .metric-label { color: #6b7280; font-size: 0.85rem; margin-bottom: 0.25rem; }
    .metric-value { color: #111827; font-size: 1.6rem; font-weight: 700; line-height: 1.1; }
    .duty-card {
        background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 20px; padding: 1rem 1rem 0.9rem 1rem;
        margin-bottom: 0.9rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .duty-card-done {
        background: #f9fafb; border: 1px solid #e5e7eb;
        border-radius: 20px; padding: 1rem 1rem 0.9rem 1rem;
        margin-bottom: 0.9rem; box-shadow: none; opacity: 0.6;
    }
    .duty-title { font-size: 1.05rem; font-weight: 650; color: #111827; margin-bottom: 0.6rem; line-height: 1.3; }
    .duty-title-done { font-size: 1.05rem; font-weight: 650; color: #9ca3af; margin-bottom: 0.6rem; line-height: 1.3; text-decoration: line-through; }
    .duty-row { color: #374151; font-size: 0.94rem; margin-bottom: 0.2rem; }
    .duty-row-done { color: #9ca3af; font-size: 0.94rem; margin-bottom: 0.2rem; }
    .status-pill { display: inline-block; padding: 0.28rem 0.7rem; border-radius: 999px; font-size: 0.78rem; font-weight: 650; margin-bottom: 0.75rem; }
    .status-overdue { background: #fee2e2; color: #b91c1c; }
    .status-today { background: #fef3c7; color: #92400e; }
    .status-upcoming { background: #dcfce7; color: #166534; }
    .status-future { background: #e5e7eb; color: #4b5563; }
    .status-done { background: #e5e7eb; color: #6b7280; }
    .section-label { color: #6b7280; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.5rem; margin-bottom: 0.75rem; }
    div[data-testid="stDataFrame"] { border: 1px solid #e5e7eb; border-radius: 18px; overflow: hidden; }
    section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.title("🐭 Mouse Duty Scheduler")
st.markdown('<div class="top-caption">Clean dashboard for upcoming mouse duties. Backend: <b>Book.xlsx</b></div>', unsafe_allow_html=True)

# ----------------------------
# GitHub config (from secrets)
# ----------------------------
GITHUB_TOKEN  = st.secrets["github"]["token"]
GITHUB_OWNER  = st.secrets["github"]["owner"]
GITHUB_REPO   = st.secrets["github"]["repo"]
GITHUB_BRANCH = st.secrets["github"].get("branch", "main")
JSON_PATH     = st.secrets["github"].get("json_path", "completed_tasks.json")

GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{JSON_PATH}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# ----------------------------
# GitHub read / write helpers
# ----------------------------
def gh_load_completed():
    """Fetch completed_tasks.json from GitHub. Returns (set_of_keys, sha)."""
    resp = requests.get(GITHUB_API, headers=HEADERS, params={"ref": GITHUB_BRANCH})
    if resp.status_code == 404:
        return set(), None          # file doesn't exist yet — will be created on first save
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return set(json.loads(content)), data["sha"]

def gh_save_completed(completed_set, sha):
    """Push updated completed_tasks.json to GitHub. Returns new sha."""
    content_bytes = json.dumps(sorted(completed_set), indent=2).encode("utf-8")
    payload = {
        "message": f"Update completed tasks [{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}]",
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha        # required for updates; omit on first create
    resp = requests.put(GITHUB_API, headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()["content"]["sha"]

# ----------------------------
# Load completed tasks into session state (once per session)
# ----------------------------
if "completed_tasks" not in st.session_state:
    with st.spinner("Loading saved completions from GitHub…"):
        try:
            completed, sha = gh_load_completed()
            st.session_state.completed_tasks = completed
            st.session_state.completed_sha   = sha
        except Exception as e:
            st.warning(f"Could not load completed tasks from GitHub: {e}")
            st.session_state.completed_tasks = set()
            st.session_state.completed_sha   = None

def toggle_task(task_key, checked):
    """Update session state and push to GitHub immediately."""
    if checked:
        st.session_state.completed_tasks.add(task_key)
    else:
        st.session_state.completed_tasks.discard(task_key)
    try:
        new_sha = gh_save_completed(
            st.session_state.completed_tasks,
            st.session_state.completed_sha
        )
        st.session_state.completed_sha = new_sha
    except Exception as e:
        st.error(f"Could not save to GitHub: {e}")

def make_task_key(mouse_id, task_name):
    return f"{mouse_id}||{task_name}"

# ----------------------------
# Load Excel data
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
    'Surgery Date':               'Chung-wei',
    'ABR Baseline 1  (day -3)':   'Kunpeng',
    'ABR Baseline 2 (day -1)':    'Kunpeng',
    'NIHL (Day 0)':               'Tinghan',
    'Exposed ABR1  (Day +1)':     'Kunpeng',
    'Exposed ABR 2  (Day +3)':    'Kunpeng',
    'Exposed ABR3 (Day +13)':     'Kunpeng',
    'Exposed ABR3  (Day +15)':    'Kunpeng',
}

id_col      = 'Mouse ID'
arrival_col = 'BCM arrival Date'

date_cols = [arrival_col] + list(task_owner_map.keys())
for col in date_cols:
    if col in tbl.columns:
        tbl[col] = pd.to_datetime(tbl[col], errors='coerce')

# ----------------------------
# Sidebar controls
# ----------------------------
st.sidebar.title("Filters")
people          = sorted(set(task_owner_map.values()))
selected_person = st.sidebar.selectbox("Person", people)
view_mode       = st.sidebar.radio("View", ["All active", "Today only", "Upcoming window", "Include future"], index=0)
days_ahead      = st.sidebar.number_input("Upcoming within days", min_value=1, value=14)
mobile_view     = st.sidebar.toggle("📱 Mobile card view", value=True)
show_summary    = st.sidebar.toggle("Show summary cards", value=True)
show_completed  = st.sidebar.toggle("Show completed tasks", value=True)

# ----------------------------
# Build duty list
# ----------------------------
today = datetime.today().date()
rows  = []

for _, row in tbl.iterrows():
    mouse_id    = str(row.get(id_col, ''))
    arrival     = row.get(arrival_col)
    arrival_str = arrival.strftime('%m/%d/%Y') if pd.notna(arrival) else ''

    for task_name, owner in task_owner_map.items():
        if owner != selected_person:
            continue
        if task_name not in tbl.columns:
            continue
        due = row.get(task_name)
        if pd.isna(due):
            continue

        due_date  = due.date() if isinstance(due, pd.Timestamp) else due
        days_left = (due_date - today).days
        task_key  = make_task_key(mouse_id, task_name)
        is_done   = task_key in st.session_state.completed_tasks

        if days_left < 0:
            status = "Overdue"
        elif days_left == 0:
            status = "Today"
        elif days_left <= days_ahead:
            status = "Upcoming"
        else:
            status = "Future"

        if not show_completed and is_done:
            continue

        if not is_done:
            if view_mode == "Today only" and status != "Today":
                continue
            elif view_mode == "Upcoming window" and status not in ["Today", "Upcoming"]:
                continue
            elif view_mode == "All active" and status == "Future":
                continue

        rows.append({
            "Status":       status,
            "Person":       owner,
            "Mouse ID":     mouse_id,
            "Task":         task_name,
            "Due Date":     due_date.strftime('%m/%d/%Y'),
            "Days Left":    days_left,
            "Arrival Date": arrival_str,
            "_sort_due":    due_date,
            "_task_key":    task_key,
            "_is_done":     is_done,
        })

if not rows:
    st.warning(f"No duties found for {selected_person}.")
    st.stop()

df = pd.DataFrame(rows).sort_values(
    by=["_is_done", "_sort_due", "Mouse ID", "Task"]
).reset_index(drop=True)

# ----------------------------
# Summary cards
# ----------------------------
active_df = df[~df["_is_done"]]
n_overdue  = int((active_df["Status"] == "Overdue").sum())
n_today    = int((active_df["Status"] == "Today").sum())
n_total    = len(active_df)
n_done     = int(df["_is_done"].sum())

if show_summary:
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val in [
        (c1, "Person",        selected_person),
        (c2, "Active duties", n_total),
        (c3, "Due today",     n_today),
        (c4, "Overdue",       n_overdue),
        (c5, "✅ Completed",  n_done),
    ]:
        size = "font-size:1.15rem;" if label == "Person" else ""
        col.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value" style="{size}">{val}</div></div>',
            unsafe_allow_html=True
        )

st.markdown('<div class="section-label">Duty list</div>', unsafe_allow_html=True)

# ----------------------------
# Mobile card view
# ----------------------------
if mobile_view:
    for _, r in df.iterrows():
        task_key = r["_task_key"]
        is_done  = r["_is_done"]

        if is_done:
            status_class = "status-pill status-done"
            icon = "✅"; card_class = "duty-card-done"
            title_class = "duty-title-done"; row_class = "duty-row-done"
            status_label = "Done"
        else:
            status_label = r["Status"]
            icon_map  = {"Overdue": "🔴", "Today": "🟡", "Upcoming": "🟢"}
            class_map = {"Overdue": "status-overdue", "Today": "status-today",
                         "Upcoming": "status-upcoming", "Future": "status-future"}
            icon         = icon_map.get(r["Status"], "⚪")
            status_class = f"status-pill {class_map.get(r['Status'], 'status-future')}"
            card_class   = "duty-card"; title_class = "duty-title"; row_class = "duty-row"

        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        col_check, col_content = st.columns([0.08, 0.92])

        with col_check:
            checked = st.checkbox("Done", value=is_done,
                                  key=f"chk_{task_key}", label_visibility="collapsed")
        with col_content:
            st.markdown(f'''
                <div class="{status_class}">{status_label}</div>
                <div class="{title_class}">{icon} {r["Task"]}</div>
                <div class="{row_class}"><b>Mouse ID:</b> {r["Mouse ID"]}</div>
                <div class="{row_class}"><b>Due Date:</b> {r["Due Date"]}</div>
                <div class="{row_class}"><b>Days Left:</b> {r["Days Left"]}</div>
                <div class="{row_class}"><b>Arrival Date:</b> {r["Arrival Date"]}</div>
                <div class="{row_class}"><b>Owner:</b> {r["Person"]}</div>
            ''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        if checked != is_done:
            toggle_task(task_key, checked)
            st.rerun()

# ----------------------------
# Desktop / table view
# ----------------------------
else:
    st.markdown("**Check a task to mark it complete:**")
    for _, r in df.iterrows():
        task_key = r["_task_key"]
        is_done  = r["_is_done"]
        fmt      = lambda s: f"~~{s}~~" if is_done else str(s)

        cols = st.columns([0.05, 0.1, 0.25, 0.18, 0.1, 0.15, 0.12])
        with cols[0]:
            checked = st.checkbox("", value=is_done,
                                  key=f"chk_{task_key}", label_visibility="collapsed")
        for col, val in zip(cols[1:], ["Status", "Task", "Mouse ID", "Due Date", "Days Left", "Person"]):
            col.markdown(fmt(r[val]))

        if checked != is_done:
            toggle_task(task_key, checked)
            st.rerun()

# ----------------------------
# Footer
# ----------------------------
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Refresh Data", use_container_width=True):
        st.rerun()

with col2:
    if st.button("🗑️ Clear All Completed", use_container_width=True):
        st.session_state.completed_tasks = set()
        try:
            new_sha = gh_save_completed(set(), st.session_state.completed_sha)
            st.session_state.completed_sha = new_sha
        except Exception as e:
            st.error(f"Could not save to GitHub: {e}")
        st.rerun()

with col3:
    st.caption(f"Last loaded: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}")
