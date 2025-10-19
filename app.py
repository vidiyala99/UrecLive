import streamlit as st
import requests
from datetime import datetime, timezone
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from firebase_auth import signup_user, signin_user

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="UREC Live Dashboard", page_icon="💪", layout="wide")

# -------------------- CSS --------------------
st.markdown("""
<style>
.stApp { background:#0e1117; color:#e5e7eb; }
h1, h2, h3 { letter-spacing:.2px; }
.urec-gradient {
  background:linear-gradient(90deg,#34d399,#60a5fa,#c084fc);
  -webkit-background-clip:text; color:transparent;
}
.glass {
  background:rgba(255,255,255,0.06);
  border:1px solid rgba(255,255,255,0.08);
  border-radius:18px; padding:18px 20px;
  box-shadow:0 10px 30px rgba(0,0,0,0.25);
}
.stButton>button {
  border-radius:12px !important;
  border:1px solid rgba(255,255,255,0.12)!important;
  background:#1f2937!important; color:#e5e7eb!important;
  padding:10px 14px!important;
}
.overlay {
  max-width:680px; margin:7vh auto; padding:28px;
  border-radius:20px; background:rgba(17,24,39,0.75);
  border:1px solid rgba(255,255,255,0.1);
  box-shadow:0 20px 80px rgba(0,0,0,0.55);
}
.sugg-card {
  background:rgba(255,255,255,0.04);
  border:1px solid rgba(255,255,255,0.08);
  border-radius:14px; padding:14px 16px; margin:8px 0;
}
.disabled-btn {
  opacity:0.4; pointer-events:none;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# CONSTANTS
# =====================================================
API_URL = "http://127.0.0.1:8000/analytics/heatmap"
EQUIPMENTS_URL = "http://127.0.0.1:8000/equipments"
USAGE_UPDATE_URL = "http://127.0.0.1:8000/usage_logs/update"
EXERCISES_URL = "http://127.0.0.1:8000/exercises"
REFRESH_INTERVAL = 10  # seconds

AVG_SESSION_TIME_BY_ZONE = {
    "cardio": 20, "dumbbells": 12, "benches": 15,
    "squat racks": 25, "back machines": 18,
    "bicep machines": 10, "tricep machines": 12,
    "shoulder machines": 14, "quad machines": 16,
    "glute machines": 18, "leg machines": 20
}
DEFAULT_SESSION = 20

# =====================================================
# SESSION STATE
# =====================================================
defaults = {
    "user_id": None, "user_name": None,
    "auth_complete": False, "stage": "login",
    "selected_group": None, "switch_target": None,
    "show_modal": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# HELPERS
# =====================================================
def rerun_safe():
    """Handle Streamlit rerun compatibly."""
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

def fetch_json(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def post_usage_update(zone, status):
    """Update usage status in backend"""
    payload = {
        "zone": zone,
        "status": status,
        "user": st.session_state.user_name or "demo_user",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        return requests.post(USAGE_UPDATE_URL, json=payload, timeout=10)
    except:
        return None


def get_eta_for_zone(zone, utilization):
    avg_time = AVG_SESSION_TIME_BY_ZONE.get(zone.lower(), DEFAULT_SESSION)
    return int((utilization / 100.0) * avg_time)


@st.cache_data(ttl=120)
def fetch_workout_library():
    """Fetch all exercises once from backend"""
    try:
        data = fetch_json(EXERCISES_URL)
        if not data or "exercises" not in data:
            return {}
        workout_library = {}
        for ex in data["exercises"]:
            muscle = ex.get("primary_muscle", "Other")
            workout_library.setdefault(muscle, []).append({
                "name": ex.get("exercise_name"),
                "zone": ex.get("equipment_type"),
            })
        return workout_library
    except Exception as e:
        print("Error fetching workout library:", e)
        return {}


WORKOUT_LIBRARY = fetch_workout_library()

# =====================================================
# LOGIN
# =====================================================
def login_screen():
    st.markdown('<div class="overlay">', unsafe_allow_html=True)
    st.markdown("<h2 class='urec-gradient'>🔐 Welcome to UREC Live</h2>", unsafe_allow_html=True)
    mode = st.radio("Mode:", ["Login", "Sign Up"], horizontal=True)
    with st.form("auth_form"):
        email = st.text_input("📧 Email")
        password = st.text_input("🔑 Password", type="password")
        submit = st.form_submit_button("Continue →")

    if submit:
        if not email or not password:
            st.warning("Please fill both fields.")
        else:
            try:
                if mode == "Sign Up":
                    signup_user(email, password)
                    st.success("✅ Account created! You can now log in.")
                else:
                    res = signin_user(email, password)
                    st.session_state.user_name = email.split("@")[0]
                    st.session_state.user_id = res["localId"]
                    st.session_state.auth_complete = True
                    st.session_state.stage = "welcome"
                    rerun_safe()
            except Exception as e:
                st.error(str(e))
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# =====================================================
# HEATMAP PANEL
# =====================================================
def render_heatmap_panel():
    st.markdown("### 🌡️ Live Gym Occupancy Overview")
    data = fetch_json(API_URL)
    if not data or "zones" not in data:
        st.warning("No live data available.")
        return

    zones = data["zones"]
    df = pd.DataFrame([{"Zone": k, "Utilization": v.get("utilization_percent", 0)} for k, v in zones.items()])
    st.bar_chart(df.set_index("Zone"))

    # Historical mock trend
    st.markdown("#### ⏱ Historical Utilization Trend (Simulated)")
    times = pd.date_range(end=datetime.now(), periods=12, freq="H")
    mock_data = pd.DataFrame({
        "Time": times,
        "Occupancy %": [min(100, abs(60 + 30 * (i % 4 - 2))) for i in range(len(times))],
    }).set_index("Time")
    st.area_chart(mock_data)
    st.caption("💡 Scroll through hours to find less active times (simulated trend).")

# =====================================================
# CHECK-IN STATUS
# =====================================================
def get_current_checkin():
    user = st.session_state.user_name or "demo_user"
    data = fetch_json(EQUIPMENTS_URL)
    if not data:
        return None

    user = user.strip().lower()
    for e in data:
        if e.get("current_user", "").strip().lower() == user and e.get("status", "").lower() in ["in_use", "occupied"]:
            return e
    return None


def render_current_status(current):
    if not current:
        st.info("✅ You are not checked into any equipment.")
        return

    zone = current.get("zone") or current.get("equipment_type")
    eq_id = current.get("equipment_id")
    st.markdown(f"### 🧍 Checked into: **{zone} ({eq_id})**")

    if st.button(f"🏁 Check Out from {zone}", key=f"checkout_{eq_id}"):
        with st.spinner("Processing checkout..."):
            r = post_usage_update(zone, "available")
        if r and r.status_code in (200, 201):
            st.success(f"✅ Checked out from {zone}. Returning to dashboard...")
            st.session_state["selected_group"] = None
            st.session_state["stage"] = "welcome"
            st.cache_data.clear()
            rerun_safe()
        else:
            st.error("❌ Something went wrong while checking out.")

# =====================================================
# SMART SUGGESTIONS
# =====================================================
def render_suggestions(data, group, current):
    zones = data.get("zones", {})
    suggestions = []
    for item in WORKOUT_LIBRARY.get(group, []):
        z = item["zone"].lower()
        stats = zones.get(z, {"utilization_percent": 0})
        util = float(stats.get("utilization_percent", 0))
        eta = get_eta_for_zone(z, util)
        suggestions.append({"name": item["name"], "zone": z, "eta": eta, "util": util})

    suggestions.sort(key=lambda x: x["eta"])
    st.markdown("### 🧠 <span class='urec-gradient'>Smart Workout Suggestions</span>", unsafe_allow_html=True)

    for s in suggestions:
        dot = "🟢" if s["util"] < 30 else ("🟡" if s["util"] < 70 else "🔴")
        st.markdown(f"""
        <div class='sugg-card'>
          <b>{s['name']}</b> ({s['zone']})<br>
          ETA: {s['eta']} min | {dot}
        </div>
        """, unsafe_allow_html=True)

        if current and current.get("zone", "").lower() == s["zone"]:
            st.markdown("<div class='disabled-btn'>Already checked in</div>", unsafe_allow_html=True)
            continue

        if st.button(f"✅ Check In to {s['zone']}", key=f"sugg_{s['zone']}_{s['name']}"):
            with st.spinner(f"Checking into {s['zone']}..."):
                r = post_usage_update(s["zone"], "in_use")
            if r and r.status_code in (200, 201):
                st.success(f"✅ Checked into {s['zone']} successfully!")
                rerun_safe()
            else:
                st.error("❌ Could not check in. Please retry.")

# =====================================================
# MAIN FLOW
# =====================================================
st.markdown("<h1 class='urec-gradient'>🏋️ UREC Live Equipment Dashboard</h1>", unsafe_allow_html=True)
st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="autorefresh")

if not st.session_state.auth_complete:
    login_screen()

col1, col2 = st.columns([2, 1])

with col1:
    if st.session_state.stage == "welcome":
        st.markdown(f"### 👋 Welcome, **{st.session_state.user_name}**!")
        group = st.selectbox("Choose muscle group:", list(WORKOUT_LIBRARY.keys()), index=None, placeholder="Select...")
        if group and st.button("Show My Plan 🚀"):
            st.session_state.stage = "recommend"
            st.session_state.selected_group = group
            rerun_safe()

    elif st.session_state.stage == "recommend":
        data = fetch_json(API_URL)
        if not data:
            st.warning("⚠️ No data available.")
        else:
            current = get_current_checkin()
            render_current_status(current)
            st.markdown("<hr style='opacity:0.2;'>", unsafe_allow_html=True)
            render_suggestions(data, st.session_state.selected_group, current)

with col2:
    render_heatmap_panel()
