import streamlit as st
import requests
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh
from firebase_auth import signup_user, signin_user  # Firebase helpers

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
USAGE_UPDATE_URL = "http://127.0.0.1:8000/usage_logs/update"
EQUIPMENTS_URL = "http://127.0.0.1:8000/equipments"
REFRESH_INTERVAL = 5  # seconds

# Adaptive session averages (mins)
AVG_SESSION_TIME_BY_ZONE = {
    "cardio": 20,
    "dumbbells": 12,
    "benches": 15,
    "squat racks": 25,
    "Back Machines": 18,
}
DEFAULT_SESSION = 20

WORKOUT_LIBRARY = {
    "Chest": [
        {"name": "Bench Press", "zone": "benches"},
        {"name": "Incline Dumbbell Press", "zone": "dumbbells"},
    ],
    "Back": [
        {"name": "Lat Pulldown", "zone": "Back Machines"},
        {"name": "Seated Row", "zone": "Back Machines"},
    ],
    "Legs": [
        {"name": "Back Squat", "zone": "squat racks"},
        {"name": "Leg Extension", "zone": "Back Machines"},
    ],
    "Arms": [
        {"name": "Bicep Curls", "zone": "dumbbells"},
        {"name": "Tricep Pushdown", "zone": "Back Machines"},
    ],
    "Core": [
        {"name": "Weighted Crunch", "zone": "dumbbells"},
        {"name": "Cable Woodchop", "zone": "Back Machines"},
    ],
    "Cardio": [
        {"name": "Treadmill Run", "zone": "cardio"},
        {"name": "Bike Intervals", "zone": "cardio"},
    ],
}

# =====================================================
# SESSION STATE
# =====================================================
defaults = {
    "user_id": None,
    "user_name": None,
    "auth_complete": False,
    "stage": "login",
    "selected_group": None,
    "switch_target": None,
    "show_modal": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# API HELPERS
# =====================================================
def fetch_json(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def post_usage_update(zone, status):
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
    avg_time = AVG_SESSION_TIME_BY_ZONE.get(zone, DEFAULT_SESSION)
    return int((utilization / 100.0) * avg_time)

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
                    st.rerun()
            except Exception as e:
                st.error(str(e))
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# =====================================================
# CURRENT CHECK-IN STATUS + SWITCH LOGIC
# =====================================================
def get_current_checkin():
    user = st.session_state.user_name or "demo_user"
    data = fetch_json(EQUIPMENTS_URL)
    if not data:
        return None
    active = [e for e in data if e.get("current_user") == user and e.get("status") == "in_use"]
    return active[0] if active else None

def render_current_status(current):
    st.markdown("### 🧍 Current Check-In Status")
    if not current:
        st.info("✅ You are not checked into any equipment.")
        return

    zone = current.get("zone")
    eq_id = current.get("equipment_id")
    start_time = current.get("start_time")

    st.markdown(f"""
    <div class="glass">
      <b>Equipment:</b> {eq_id}<br>
      <b>Zone:</b> {zone}<br>
      <b>Start Time:</b> {start_time}
    </div>
    """, unsafe_allow_html=True)

    heatmap = fetch_json(API_URL)
    available_zones = []
    if heatmap and "zones" in heatmap:
        available_zones = [
            z for z, v in heatmap["zones"].items()
            if v.get("available", 0) > 0 and z != zone
        ]

    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"🏁 Check Out from {zone}", key=f"checkout_{eq_id}"):
            r = post_usage_update(zone, "available")
            if r and r.status_code in (200, 201):
                st.success(f"✅ Checked out from {zone}.")
                st.rerun()
            else:
                st.error("Something went wrong while checking out.")

    with c2:
        st.session_state["switch_target"] = st.selectbox(
            "Switch to another available zone:",
            [None] + available_zones,
            key="switch_select",
        )
        if st.session_state["switch_target"]:
            if st.button("🔁 Confirm Switch"):
                st.session_state.show_modal = True
                st.session_state.modal_from = zone
                st.session_state.modal_to = st.session_state["switch_target"]
                st.session_state.heatmap_snapshot = heatmap
                st.rerun()

# =====================================================
# SWITCH CONFIRMATION MODAL WITH ADAPTIVE ETA
# =====================================================
# =====================================================
# SWITCH CONFIRMATION "MODAL" (custom overlay version)
# =====================================================
# =====================================================
# SWITCH CONFIRMATION "MODAL" (animated overlay)
# =====================================================
# =====================================================
# SWITCH CONFIRMATION MODAL (with ✖ Close + fade animation)
# =====================================================
def render_modal():
    if st.session_state.show_modal:
        st.markdown("""
        <style>
        /* ===== Overlay background ===== */
        .overlay-bg {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.65);
            z-index: 999;
            display: flex;
            justify-content: center;
            align-items: center;
            animation: fadeIn 0.3s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.96); }
            to { opacity: 1; transform: scale(1); }
        }

        /* ===== Modal box ===== */
        .overlay-box {
            position: relative;
            background: #1f2937;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 18px;
            padding: 32px 34px;
            width: 430px;
            color: #e5e7eb;
            text-align: center;
            box-shadow: 0 12px 45px rgba(0,0,0,0.5);
            animation: fadeInUp 0.35s ease-out;
            z-index: 1000;
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ===== Close icon ===== */
        .close-btn {
            position: absolute;
            top: 12px;
            right: 14px;
            font-size: 20px;
            color: #9ca3af;
            cursor: pointer;
            transition: color 0.2s ease, transform 0.2s ease;
        }
        .close-btn:hover {
            color: #f87171;
            transform: scale(1.15);
        }

        /* ===== Ensure Streamlit components are clickable ===== */
        [data-testid="stAppViewContainer"] {
            pointer-events: auto !important;
        }
        </style>
        """, unsafe_allow_html=True)

        from_zone = st.session_state.modal_from
        to_zone = st.session_state.modal_to
        heatmap = st.session_state.heatmap_snapshot

        zone_stats = heatmap["zones"].get(to_zone, {})
        util = zone_stats.get("utilization_percent", 0)
        eta = get_eta_for_zone(to_zone, util)
        color = "🟢" if util < 30 else ("🟡" if util < 70 else "🔴")
        avg_time = AVG_SESSION_TIME_BY_ZONE.get(to_zone, DEFAULT_SESSION)

        # ===== Render modal HTML =====
        st.markdown(f"""
        <div class="overlay-bg">
          <div class="overlay-box">
            <div class="close-btn" onclick="window.parent.postMessage({{type: 'close_modal'}}, '*')">✖</div>
            <h3 style='margin-bottom:12px;'>⚠️ Confirm Zone Switch</h3>
            <p>You're about to switch from <b>{from_zone}</b> → <b>{to_zone}</b></p>
            <p>{color} <b>{to_zone.capitalize()} Zone:</b> {util}% utilized</p>
            <p>⏱ Typical session: {avg_time} min<br>⏳ Estimated wait ≈ <b>{eta} min</b></p>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ===== Buttons below modal =====
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Yes, Switch", key="modal_yes"):
                r1 = post_usage_update(from_zone, "available")
                r2 = post_usage_update(to_zone, "in_use")
                if r1 and r1.status_code in (200, 201) and r2 and r2.status_code in (200, 201):
                    st.success(f"✅ Switched from {from_zone} → {to_zone}.")
                    st.session_state.show_modal = False
                    st.session_state.switch_target = None
                    st.rerun()
                else:
                    st.error("Something went wrong while switching zones.")
        with c2:
            if st.button("❌ Cancel", key="modal_cancel"):
                st.session_state.show_modal = False
                st.session_state.switch_target = None
                st.rerun()

        # ===== Handle close button clicks =====
        st.markdown("""
        <script>
        window.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'close_modal') {
                window.parent.postMessage({type: 'streamlit_close_modal'}, '*');
            }
        });
        </script>
        """, unsafe_allow_html=True)


# =====================================================
# SMART SUGGESTIONS
# =====================================================
def render_suggestions(data, group, current):
    zones = data.get("zones", {})
    suggestions = []
    for item in WORKOUT_LIBRARY.get(group, []):
        z = item["zone"]
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

        disabled = current and current.get("zone") != s["zone"]

        if disabled:
            st.markdown(f"<div class='disabled-btn'><button disabled>✅ Check In to {s['zone']}</button></div>", unsafe_allow_html=True)
        else:
            if st.button(f"✅ Check In to {s['zone']}", key=f"sugg_{s['zone']}_{s['name']}"):
                r = post_usage_update(s["zone"], "in_use")
                if r and r.status_code in (200, 201):
                    st.success(f"✅ Checked into {s['zone']}.")
                    st.rerun()
                else:
                    st.error("Could not check in. Please retry.")

# =====================================================
# MAIN FLOW
# =====================================================
st.markdown("<h1 class='urec-gradient'>🏋️ UREC Live Equipment Dashboard</h1>", unsafe_allow_html=True)
st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="autorefresh")

if not st.session_state.auth_complete:
    login_screen()

if st.session_state.stage == "welcome":
    st.markdown(f"### 👋 Welcome, **{st.session_state.user_name}**!")
    group = st.selectbox("Choose muscle group:", list(WORKOUT_LIBRARY.keys()), index=None, placeholder="Select...")
    if group and st.button("Show My Plan 🚀"):
        st.session_state.stage = "recommend"
        st.session_state.selected_group = group
        st.rerun()

elif st.session_state.stage == "recommend":
    data = fetch_json(API_URL)
    if not data:
        st.warning("No data available.")
    else:
        current = get_current_checkin()
        render_current_status(current)
        render_modal()  # ✅ includes adaptive ETA
        st.markdown("<hr style='opacity:0.2;'>", unsafe_allow_html=True)
        render_suggestions(data, st.session_state.selected_group, current)
else:
    login_screen()
