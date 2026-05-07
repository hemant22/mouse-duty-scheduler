import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, date
import re

# ============================================================
# Streamlit page config
# ============================================================
st.set_page_config(
    page_title="NIHL / ABR Mouse Scheduler",
    page_icon="🐭",
    layout="wide"
)

# ============================================================
# Fancy CSS
# ============================================================
st.markdown("""
<style>
    .block-container { padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1400px; }
    h1, h2, h3 { letter-spacing: -0.03em; }
    .top-caption { color:#64748b; font-size:0.98rem; margin-bottom:1.2rem; }

    .metric-card {
        background: linear-gradient(180deg,#ffffff,#f8fafc);
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 1rem;
        box-shadow: 0 6px 20px rgba(15,23,42,0.06);
    }
    .metric-label { color:#64748b; font-size:0.82rem; font-weight:650; text-transform:uppercase; letter-spacing:0.06em; }
    .metric-value { color:#0f172a; font-size:1.7rem; font-weight:800; margin-top:0.25rem; }

    .duty-card {
        border: 1px solid #e2e8f0;
        border-radius: 24px;
        padding: 1rem 1rem 0.9rem 1rem;
        margin-bottom: 1rem;
        background: rgba(255,255,255,0.96);
        box-shadow: 0 10px 28px rgba(15,23,42,0.08);
    }
    .duty-card-done {
        border: 1px solid #e5e7eb;
        border-radius: 24px;
        padding: 1rem 1rem 0.9rem 1rem;
        margin-bottom: 1rem;
        background: #f8fafc;
        opacity: 0.58;
    }
    .task-title { font-size: 1.08rem; font-weight: 800; color:#0f172a; margin-bottom:0.3rem; }
    .task-title-done { font-size: 1.08rem; font-weight: 800; color:#94a3b8; margin-bottom:0.3rem; text-decoration: line-through; }
    .duty-row { font-size:0.94rem; color:#334155; margin-bottom:0.17rem; }
    .duty-row-done { font-size:0.94rem; color:#94a3b8; margin-bottom:0.17rem; }

    .pill { display:inline-block; padding:0.26rem 0.68rem; border-radius:999px; font-size:0.76rem; font-weight:800; margin-bottom:0.65rem; }
    .overdue { background:#fee2e2; color:#991b1b; }
    .today { background:#fef3c7; color:#92400e; }
    .upcoming { background:#dcfce7; color:#166534; }
    .future { background:#e2e8f0; color:#475569; }
    .done { background:#e5e7eb; color:#64748b; }
    .heavy { background:#ede9fe; color:#5b21b6; }
    .nihl { background:#fee2e2; color:#b91c1c; }
    .baseline { background:#dbeafe; color:#1d4ed8; }
    .post { background:#ffedd5; color:#c2410c; }
    .surgery { background:#fce7f3; color:#9d174d; }

    .ear-wrap { display:flex; gap:0.45rem; align-items:center; margin-top:0.55rem; }
    .ear-box { border:1px solid #e2e8f0; border-radius:18px; padding:0.45rem 0.5rem; min-width:74px; text-align:center; background:#f8fafc; }
    .ear-box-active-left { border:2px solid #2563eb; background:#dbeafe; box-shadow: 0 0 0 4px rgba(37,99,235,0.10); }
    .ear-box-active-right { border:2px solid #dc2626; background:#fee2e2; box-shadow: 0 0 0 4px rgba(220,38,38,0.10); }
    .ear-label { font-size:0.72rem; font-weight:800; color:#475569; text-transform:uppercase; letter-spacing:0.06em; }
    .ear-icon { font-size:1.55rem; line-height:1.1; }

    .section-label { color:#64748b; font-size:0.82rem; text-transform:uppercase; letter-spacing:0.08em; margin-top:1.0rem; margin-bottom:0.8rem; font-weight:800; }
    div[data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 18px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

st.title("🐭 NIHL / ABR Mouse Scheduler")
st.markdown('<div class="top-caption">Fancy dashboard from <b>Book.xlsx</b>. Shows duty date, ear side, workload weight, and task completion.</div>', unsafe_allow_html=True)

# ============================================================
# GitHub config for completed-task persistence
# ============================================================
def github_is_configured():
    try:
        return "github" in st.secrets
    except Exception:
        # No secrets.toml present (e.g. running locally without GitHub config) -> just disable persistence.
        return False

if github_is_configured():
    GITHUB_TOKEN  = st.secrets["github"].get("token", "")
    GITHUB_OWNER  = st.secrets["github"].get("owner", "")
    GITHUB_REPO   = st.secrets["github"].get("repo", "")
    GITHUB_BRANCH = st.secrets["github"].get("branch", "main")
    JSON_PATH     = st.secrets["github"].get("json_path", "completed_tasks.json")
    GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{JSON_PATH}"
    HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
else:
    GITHUB_API, HEADERS, GITHUB_BRANCH = None, None, None

def gh_load_completed():
    if not github_is_configured():
        return set(), None
    resp = requests.get(GITHUB_API, headers=HEADERS, params={"ref": GITHUB_BRANCH}, timeout=20)
    if resp.status_code == 404:
        return set(), None
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return set(json.loads(content)), data["sha"]

def gh_save_completed(completed_set, sha):
    if not github_is_configured():
        return sha
    content_bytes = json.dumps(sorted(completed_set), indent=2).encode("utf-8")
    payload = {
        "message": f"Update completed tasks [{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}]",
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(GITHUB_API, headers=HEADERS, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()["content"]["sha"]

if "completed_tasks" not in st.session_state:
    try:
        completed, sha = gh_load_completed()
        st.session_state.completed_tasks = completed
        st.session_state.completed_sha = sha
    except Exception as e:
        st.warning(f"Could not load saved completions from GitHub: {e}")
        st.session_state.completed_tasks = set()
        st.session_state.completed_sha = None

def toggle_task(task_key, checked):
    if checked:
        st.session_state.completed_tasks.add(task_key)
    else:
        st.session_state.completed_tasks.discard(task_key)
    try:
        st.session_state.completed_sha = gh_save_completed(st.session_state.completed_tasks, st.session_state.completed_sha)
    except Exception as e:
        st.error(f"Could not save completion status: {e}")

def make_task_key(mouse_id, task_name, due_date):
    return f"{mouse_id}||{task_name}||{due_date}"

# ============================================================
# Load Excel
# ============================================================
# New layout: rows 0-2 contain instructions/title, header row is on Excel row 4 -> pandas header=3
EXCEL_FILE = "Book.xlsx"

def load_table(path):
    """Find the real header row (the one containing 'Mouse ID') and load from there.
    This is robust against extra title/instruction rows being inserted at the top."""
    raw = pd.read_excel(path, header=None)
    header_row = None
    for i in range(min(15, len(raw))):
        row_vals = [str(v).strip().lower() for v in raw.iloc[i].tolist()]
        if any(v == "mouse id" for v in row_vals):
            header_row = i
            break
    if header_row is None:
        # Fallback to the layout we observed
        header_row = 3
    df = pd.read_excel(path, header=header_row)
    return df

try:
    tbl = load_table(EXCEL_FILE)
except Exception as e:
    st.error(f"Could not read {EXCEL_FILE}: {e}")
    st.stop()

# Flatten/clean headers that may contain line breaks
tbl.columns = [str(c).replace("\n", " ").strip() for c in tbl.columns]

# ============================================================
# Robust column detection
# ============================================================
def normalize(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()

def find_col(required_words, optional_words=None):
    optional_words = optional_words or []
    required_words = [w.lower() for w in required_words]
    optional_words = [w.lower() for w in optional_words]
    candidates = []
    for c in tbl.columns:
        n = normalize(c)
        if all(w in n for w in required_words):
            score = sum(w in n for w in optional_words)
            candidates.append((score, c))
    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0][1]

id_col      = find_col(["mouse", "id"]) or "Mouse ID"
arrival_col = find_col(["arrival"]) or "BCM arrival Date"
surgery_col = find_col(["surgery"])
sound_col   = find_col(["sound", "level"])

# ============================================================
# Drop the legend / "Day +N" / "Protocol Day" / blank rows that sit at the
# bottom of the sheet. A real mouse row must:
#   (a) have a non-empty Mouse ID,
#   (b) have a Mouse ID that is NOT a protocol-day legend (e.g. "Day -4",
#       "Day +1", "Day 0", "Protocol Day"),
#   (c) have a parseable BCM arrival Date that is a real date (not the
#       small integers used in the offset legend).
# ============================================================
if arrival_col in tbl.columns:
    tbl[arrival_col] = pd.to_datetime(tbl[arrival_col], errors="coerce")

if id_col in tbl.columns:
    mid_str = tbl[id_col].astype(str).str.strip()
    blank_id = mid_str.isin(["", "nan", "None", "NaT"])
    legend_id = mid_str.str.contains(r"\b(?:day|protocol)\b", case=False, regex=True, na=False)
    bad_mask = blank_id | legend_id
    if arrival_col in tbl.columns:
        # Real arrivals are >= year 2000. Legend integers map to ~1970.
        bad_mask = bad_mask | tbl[arrival_col].isna() | (tbl[arrival_col] < pd.Timestamp("2000-01-01"))
    tbl = tbl[~bad_mask].copy()

# ============================================================
# Build TASKS dynamically from the column headers
# Owner assignment rule (per user spec):
#   - Any column header containing "ABR"     -> Kunpeng
#   - Any column header containing "NIHL"    -> Tinghan
#   - The "Surgery" column                   -> Chung-wei
# ============================================================
NON_TASK_COLS = {id_col, arrival_col, sound_col}

def detect_ear(header):
    h = header.lower()
    has_left = "left" in h
    has_right = "right" in h
    if has_left and has_right:
        return "Both"
    if has_left:
        return "Left"
    if has_right:
        return "Right"
    return "None"

def detect_phase_owner_weight(header):
    """Return (phase, owner, weight) based on header text and which ear(s) are involved."""
    h = header.lower()
    ear = detect_ear(header)

    if "surgery" in h:
        return "Surgery", "Chung-wei", 0
    if "nihl" in h:
        return "NIHL", "Tinghan", 0
    if "abr" in h:
        # weight: both ears = 2, single ear = 1
        weight = 2 if ear == "Both" else 1
        if "baseline" in h:
            phase = "Baseline"
        elif "exposed" in h or "post" in h:
            phase = "Post"
        else:
            phase = "ABR"
        return phase, "Kunpeng", weight
    return None  # not a recognised task column

def short_name(header):
    """Make a compact human-readable task name from a header."""
    s = re.sub(r"\s+", " ", header).strip()
    # Strip parenthetical day info, e.g. "(day -4)" anywhere in the string
    s = re.sub(r"\s*\(\s*day[^)]*\)\s*", " ", s, flags=re.IGNORECASE).strip()
    # Strip ear descriptors at the end (allow trailing whitespace before EOL via \s*$)
    s = re.sub(r"\s*-\s*(left|right)\s*ear\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*(left|right)\s*\+\s*(left|right)\s*ear\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*(left|right)\s*ear\s*$", "", s, flags=re.IGNORECASE)
    # Drop trailing " Date" so "Surgery Date" -> "Surgery"
    s = re.sub(r"\s+date\s*$", "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()

TASKS = []
for col in tbl.columns:
    if col in NON_TASK_COLS:
        continue
    detected = detect_phase_owner_weight(col)
    if detected is None:
        continue
    phase, owner, weight = detected
    TASKS.append({
        "name": short_name(col),
        "col": col,
        "owner": owner,
        "ear": detect_ear(col),
        "phase": phase,
        "weight": weight,
    })

# Parse dates on every task column + arrival
for c in set([arrival_col] + [t["col"] for t in TASKS]):
    if c in tbl.columns:
        tbl[c] = pd.to_datetime(tbl[c], errors="coerce")

# ============================================================
# Ear visual
# ============================================================
def ear_html(ear, done=False):
    opacity = "opacity:0.55;" if done else ""
    left_active = ear in ["Left", "Both"]
    right_active = ear in ["Right", "Both"]
    left_class = "ear-box ear-box-active-left" if left_active else "ear-box"
    right_class = "ear-box ear-box-active-right" if right_active else "ear-box"
    return f"""
    <div class="ear-wrap" style="{opacity}">
        <div class="{left_class}">
            <div class="ear-icon">👂</div>
            <div class="ear-label">Left</div>
        </div>
        <div class="{right_class}">
            <div class="ear-icon" style="transform:scaleX(-1); display:inline-block;">👂</div>
            <div class="ear-label">Right</div>
        </div>
    </div>
    """

def phase_pill(phase):
    cls = {"Baseline":"baseline", "NIHL":"nihl", "Post":"post", "Surgery":"surgery", "ABR":"baseline"}.get(phase, "future")
    return f'<span class="pill {cls}">{phase}</span>'

# ============================================================
# Sidebar controls
# ============================================================
st.sidebar.title("Filters")
people = sorted(set(t["owner"] for t in TASKS))
selected_person = st.sidebar.selectbox("Person", ["All"] + people, index=0)
view_mode = st.sidebar.radio("View", ["All active", "Today only", "Upcoming window", "Include future"], index=0)
days_ahead = st.sidebar.number_input("Upcoming within days", min_value=1, max_value=365, value=21)
mobile_view = st.sidebar.toggle("📱 Card view", value=True)
show_completed = st.sidebar.toggle("Show completed tasks", value=True)
show_summary = st.sidebar.toggle("Show summary cards", value=True)
show_workload = st.sidebar.toggle("Show daily workload table", value=True)

# ============================================================
# Build duty list
# ============================================================
today = datetime.today().date()
rows = []

for _, row in tbl.iterrows():
    mouse_id = str(row.get(id_col, "")).strip()
    if mouse_id == "" or mouse_id.lower() == "nan":
        continue

    arrival = row.get(arrival_col)
    arrival_str = arrival.strftime("%m/%d/%Y") if pd.notna(arrival) else ""
    sound_level = row.get(sound_col, "") if sound_col else ""
    if pd.isna(sound_level):
        sound_level = ""

    for task in TASKS:
        if selected_person != "All" and task["owner"] != selected_person:
            continue
        due = row.get(task["col"])
        if pd.isna(due):
            continue
        due_date = due.date() if isinstance(due, pd.Timestamp) else due
        days_left = (due_date - today).days
        task_key = make_task_key(mouse_id, task["name"], due_date.isoformat())
        is_done = task_key in st.session_state.completed_tasks

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
            if view_mode == "Upcoming window" and status not in ["Today", "Upcoming"]:
                continue
            if view_mode == "All active" and status == "Future":
                continue

        rows.append({
            "Status": status,
            "Person": task["owner"],
            "Mouse ID": mouse_id,
            "Task": task["name"],
            "Phase": task["phase"],
            "Ear": task["ear"],
            "Due Date": due_date.strftime("%m/%d/%Y"),
            "Days Left": days_left,
            "Arrival Date": arrival_str,
            "Sound Level": sound_level,
            "Recording Weight": task["weight"],
            "_sort_due": due_date,
            "_task_key": task_key,
            "_is_done": is_done,
        })

if len(rows) == 0:
    st.warning("No duties found with the current filters.")
    st.stop()

df = pd.DataFrame(rows).sort_values(by=["_is_done", "_sort_due", "Mouse ID", "Task"]).reset_index(drop=True)

# ============================================================
# Summary cards
# ============================================================
active_df = df[~df["_is_done"]]
n_overdue = int((active_df["Status"] == "Overdue").sum())
n_today = int((active_df["Status"] == "Today").sum())
n_active = len(active_df)
n_done = int(df["_is_done"].sum())
weighted_today = int(active_df.loc[active_df["_sort_due"] == today, "Recording Weight"].sum()) if len(active_df) else 0

if show_summary:
    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        ("Person", selected_person),
        ("Active duties", n_active),
        ("Due today", n_today),
        ("Today ABR load", weighted_today),
        ("Completed", n_done),
    ]
    for c, (label, val) in zip([c1,c2,c3,c4,c5], cards):
        c.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

# ============================================================
# Daily workload table
# ============================================================
if show_workload:
    st.markdown('<div class="section-label">Daily workload summary</div>', unsafe_allow_html=True)
    workload = df.copy()
    workload["Date"] = workload["_sort_due"]
    workload_summary = workload.groupby("Date", as_index=False).agg(
        Events=("Task", "count"),
        Weighted_ABR_Load=("Recording Weight", "sum"),
        Mice=("Mouse ID", lambda x: ", ".join(sorted(set(map(str, x)))))
    )
    workload_summary["Date"] = workload_summary["Date"].apply(lambda d: d.strftime("%m/%d/%Y"))
    workload_summary["Overload"] = workload_summary["Weighted_ABR_Load"].apply(lambda x: "⚠️ >4" if x > 4 else "")
    st.dataframe(workload_summary, use_container_width=True, hide_index=True)

# ============================================================
# Duty list display
# ============================================================
st.markdown('<div class="section-label">Duty list</div>', unsafe_allow_html=True)

if mobile_view:
    for _, r in df.iterrows():
        task_key = r["_task_key"]
        is_done = r["_is_done"]
        if is_done:
            status_class = "pill done"
            status_label = "Done"
            card_class = "duty-card-done"
            title_class = "task-title-done"
            row_class = "duty-row-done"
            icon = "✅"
        else:
            status_label = r["Status"]
            status_map = {"Overdue":"overdue", "Today":"today", "Upcoming":"upcoming", "Future":"future"}
            icon_map = {"Overdue":"🔴", "Today":"🟡", "Upcoming":"🟢", "Future":"⚪"}
            status_class = f"pill {status_map.get(r['Status'], 'future')}"
            card_class = "duty-card"
            title_class = "task-title"
            row_class = "duty-row"
            icon = icon_map.get(r["Status"], "⚪")

        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        col_content, col_ear, col_check = st.columns([0.55, 0.25, 0.20])

        with col_content:
            st.markdown(f"""
                <span class="{status_class}">{status_label}</span>
                {phase_pill(r['Phase'])}
                <span class="pill heavy">Load: {r['Recording Weight']}</span>
                <div class="{title_class}">{icon} {r['Task']}</div>
                <div class="{row_class}"><b>Mouse ID:</b> {r['Mouse ID']}</div>
                <div class="{row_class}"><b>Due Date:</b> {r['Due Date']}</div>
                <div class="{row_class}"><b>Ear:</b> {r['Ear']}</div>
                <div class="{row_class}"><b>Days Left:</b> {r['Days Left']}</div>
                <div class="{row_class}"><b>Arrival Date:</b> {r['Arrival Date']}</div>
                <div class="{row_class}"><b>Sound Level:</b> {r['Sound Level']}</div>
                <div class="{row_class}"><b>Owner:</b> {r['Person']}</div>
            """, unsafe_allow_html=True)

        with col_ear:
            st.markdown(ear_html(r["Ear"], done=is_done), unsafe_allow_html=True)

        with col_check:
            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
            checked = st.checkbox("Done", value=is_done, key=f"chk_{task_key}")

        st.markdown("</div>", unsafe_allow_html=True)

        if checked != is_done:
            toggle_task(task_key, checked)
            st.rerun()
else:
    display_df = df[["Status", "Person", "Mouse ID", "Task", "Phase", "Ear", "Due Date", "Days Left", "Sound Level", "Recording Weight"]].copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ============================================================
# Footer actions
# ============================================================
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Refresh Data", use_container_width=True):
        st.rerun()
with col2:
    if st.button("🗑️ Clear All Completed", use_container_width=True):
        st.session_state.completed_tasks = set()
        try:
            st.session_state.completed_sha = gh_save_completed(set(), st.session_state.completed_sha)
        except Exception as e:
            st.error(f"Could not save to GitHub: {e}")
        st.rerun()
with col3:
    st.caption(f"Last loaded: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}")
