import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import uuid
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# =====================================================
# PAGE CONFIG (must be first)
# =====================================================
st.set_page_config(
    page_title="UREC Live Dashboard",
    page_icon="💪",
    layout="wide"
)

# =====================================================
# USER SESSION MANAGEMENT
# =====================================================
# Initialize session variables first
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]  # short unique ID
if "user_name" not in st.session_state:
    st.session_state.user_name = "demo_user"

# Display user info *after* initialization
st.caption(f"Logged in as: **{st.session_state.user_name}** ({st.session_state.user_id})")

# =====================================================
# ENDPOINTS & CONSTANTS
# =====================================================
API_URL = "http://127.0.0.1:8000/analytics/heatmap"
USAGE_LOGS_URL = "http://127.0.0.1:8000/usage_logs"
USAGE_UPDATE_URL = "http://127.0.0.1:8000/usage_logs/update"
REFRESH_INTERVAL = 5  # seconds

# ETA defaults (minutes)
AVG_SESSION_TIME_DEFAULT = 25
AVG_SESSION_TIME_BY_ZONE = {
    "cardio": 20,
    "dumbbells": 12,
    "benches": 15,
    "squat racks": 25,
    "Back Machines": 18,
}

# =====================================================
# THEME (Dark/Light toggle)
# =====================================================
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark"

with st.sidebar:
    st.title("⚙️ Dashboard Settings")
    st.session_state.theme_mode = st.radio(
        "🎨 Theme Mode",
        ["Dark", "Light"],
        horizontal=True,
        index=0 if st.session_state.theme_mode == "Dark" else 1
    )

if st.session_state.theme_mode == "Dark":
    BACKGROUND = "#0e1117"
    CARD_COLOR = "#1f2937"
    TEXT_COLOR = "white"
    BORDER_COLOR = "#3b3b3b"
    SUCCESS = "#22c55e"
    WARNING = "#facc15"
    ERROR = "#ef4444"
else:
    BACKGROUND = "#f9f9f9"
    CARD_COLOR = "#ffffff"
    TEXT_COLOR = "#000000"
    BORDER_COLOR = "#cccccc"
    SUCCESS = "#16a34a"
    WARNING = "#eab308"
    ERROR = "#dc2626"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {BACKGROUND}; color: {TEXT_COLOR}; }}
    .stButton > button {{
        border-radius: 10px; border: 1px solid {BORDER_COLOR};
        background-color: {CARD_COLOR}; color: {TEXT_COLOR};
        transition: 0.2s ease-in-out;
    }}
    .stButton > button:hover {{
        transform: scale(1.05);
        background-color: rgba(255,255,255,0.08);
        border-color: {WARNING};
    }}
    </style>
""", unsafe_allow_html=True)

# =====================================================
# MUSCLE GROUP → ZONES
# =====================================================
MUSCLE_ZONE_MAP = {
    "All": ["benches", "dumbbells", "Back Machines", "cardio", "squat racks"],
    "Chest": ["benches"],
    "Back": ["Back Machines"],
    "Legs": ["squat racks", "Back Machines"],
    "Arms": ["dumbbells"],
    "Core": ["dumbbells"],
    "Cardio": ["cardio"],
}

# =====================================================
# HEADER / AUTOREFRESH
# =====================================================
st.title("🏋️ UREC Live Equipment Dashboard")
st.caption("Real-time gym utilization, wait-time predictions, and check-in/out")
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="auto-refresh")

# =====================================================
# SIDEBAR CONTROLS
# =====================================================
with st.sidebar:
    st.text_input("👤 Your Name (optional)", key="user_name", value=st.session_state.user_name)
    st.caption(f"🆔 Session ID: `{st.session_state.user_id}` (auto-assigned)")
    st.write(f"⏱ Refresh every **{REFRESH_INTERVAL} seconds**")
    st.markdown("---")

# =====================================================
# API HELPERS
# =====================================================
def fetch_heatmap():
    try:
        r = requests.get(API_URL, timeout=5)
        if r.status_code == 200:
            data = r.json()
            data["fetched_at"] = datetime.now().strftime("%H:%M:%S")
            return data
        st.error(f"Heatmap error: {r.status_code} - {r.text}")
    except Exception as e:
        st.error(f"Heatmap connection error: {e}")
    return None


def fetch_usage_logs(zone: str) -> list:
    try:
        r = requests.get(f"{USAGE_LOGS_URL}/{zone}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Logs error for {zone}: {e}")
    return []


def post_usage_update(zone: str, status: str) -> requests.Response:
    """Send a usage event to the backend and return full response."""
    payload = {
        "zone": zone,
        "status": status,
        "user": st.session_state.user_name or st.session_state.user_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        r = requests.post(USAGE_UPDATE_URL, json=payload, timeout=6)
        return r
    except Exception as e:
        st.error(f"Update error: {e}")
        return None

# =====================================================
# LOGS → TIME SERIES
# =====================================================
def _parse_ts(x: str):
    if not x:
        return None
    try:
        return pd.to_datetime(x, utc=True)
    except Exception:
        return None


def logs_to_timeseries(records: list) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["ts", "utilization_percent"])

    df = pd.DataFrame(records)

    if {"timestamp", "utilization_percent"}.issubset(df.columns):
        df["ts"] = df["timestamp"].apply(_parse_ts)
        return df.dropna(subset=["ts"])[["ts", "utilization_percent"]].sort_values("ts")

    if "status" in df.columns:
        if {"start_time", "end_time"}.issubset(df.columns):
            df["start_dt"] = df["start_time"].apply(_parse_ts)
            df["end_dt"] = df["end_time"].apply(_parse_ts)
            df["ts"] = df.apply(
                lambda r: r["start_dt"] + (r["end_dt"] - r["start_dt"]) / 2
                if pd.notnull(r.get("start_dt")) and pd.notnull(r.get("end_dt"))
                else r.get("start_dt"),
                axis=1
            )
        else:
            ts_col = "timestamp" if "timestamp" in df.columns else ("ts" if "ts" in df.columns else None)
            if ts_col:
                df["ts"] = df[ts_col].apply(_parse_ts)
            else:
                return pd.DataFrame(columns=["ts", "utilization_percent"])

        df = df.dropna(subset=["ts"]).sort_values("ts")
        df["utilization_percent"] = df["status"].map(lambda s: 100.0 if str(s).lower() == "in_use" else 0.0)
        return df[["ts", "utilization_percent"]]

    if "timestamp" in df.columns:
        df["ts"] = df["timestamp"].apply(_parse_ts)
        if "utilization_percent" in df.columns:
            return df.dropna(subset=["ts"])[["ts", "utilization_percent"]].sort_values("ts")

    return pd.DataFrame(columns=["ts", "utilization_percent"])

# =====================================================
# ETA (Data-driven with fallback)
# =====================================================
def avg_session_time_for(zone: str) -> int:
    return AVG_SESSION_TIME_BY_ZONE.get(zone, AVG_SESSION_TIME_DEFAULT)

def eta_minutes(zone: str, current_util: float, ts_df: pd.DataFrame) -> int:
    base = avg_session_time_for(zone)
    if ts_df.empty:
        raw = (current_util / 100.0) * base
        return int(min(max(raw, 0), 30))
    ts_df = ts_df.copy()
    ts_df["hour"] = ts_df["ts"].dt.tz_convert("UTC").dt.hour if ts_df["ts"].dt.tz is not None else ts_df["ts"].dt.hour
    hourly = ts_df.groupby("hour")["utilization_percent"].mean().reset_index()
    this_hour = datetime.now(timezone.utc).hour
    hist_util = hourly.loc[hourly["hour"] == this_hour, "utilization_percent"]
    hist_util = float(hist_util.iloc[0]) if not hist_util.empty else ts_df["utilization_percent"].mean()
    blended_util = 0.6 * current_util + 0.4 * hist_util
    raw = (blended_util / 100.0) * base
    if blended_util > 85:
        raw *= 1.2
    return int(min(max(raw, 0), 30))

# =====================================================
# ALERTS
# =====================================================
def render_alerts(zones: dict):
    st.subheader("🚨 Live Zone Alerts")
    flagged = 0
    for zone, stats in zones.items():
        util = stats.get("utilization_percent", 0)
        if util > 85:
            st.markdown(f"<div style='background:{ERROR};padding:12px;border-radius:8px;color:white;margin-bottom:6px;'>⚠️ <b>{zone}</b> crowded ({util:.0f}%) — expect a wait.</div>", unsafe_allow_html=True)
            flagged += 1
        elif util > 60:
            st.markdown(f"<div style='background:{WARNING};padding:12px;border-radius:8px;color:black;margin-bottom:6px;'>🟡 <b>{zone}</b> moderately busy ({util:.0f}%).</div>", unsafe_allow_html=True)
            flagged += 1
        elif util > 0:
            st.markdown(f"<div style='background:{SUCCESS};padding:12px;border-radius:8px;color:white;margin-bottom:6px;'>🟢 <b>{zone}</b> has availability.</div>", unsafe_allow_html=True)
    if flagged == 0:
        st.info("✅ All zones are quiet — perfect time to train!")

# =====================================================
# ZONE CARDS (with ETA + Check-In/Out + Popup)
# =====================================================
def render_zone_cards(data: dict, selected_group: str):
    if not data or "zones" not in data:
        st.warning("No zone data available.")
        return None

    zones = data["zones"]
    allowed = MUSCLE_ZONE_MAP.get(selected_group, [])
    filtered = zones if selected_group == "All" else {z: v for z, v in zones.items() if z in allowed}

    st.subheader(f"📍 {selected_group} Zone Overview")
    st.caption(f"Last updated: {data.get('fetched_at','unknown')}")

    clicked = None
    items = list(filtered.items())
    per_row = 3

    for i in range(0, len(items), per_row):
        cols = st.columns(per_row)
        for col, (zone, stats) in zip(cols, items[i:i + per_row]):
            util = float(stats.get("utilization_percent", 0))
            avail = int(stats.get("available", 0))
            in_use = int(stats.get("in_use", 0))
            logs = fetch_usage_logs(zone)
            ts_df = logs_to_timeseries(logs)
            eta = eta_minutes(zone, util, ts_df)
            color = SUCCESS if util == 0 else (WARNING if util < 70 else ERROR)
            emoji = "🟢" if util == 0 else ("🟡" if util < 70 else "🔴")

            if col.button(f"{zone}", key=f"open_{zone}", use_container_width=True):
                clicked = zone

            col.markdown(f"""
            <div style="background:{color};border-radius:20px;padding:20px;box-shadow:0 6px 18px rgba(0,0,0,0.25);
            color:white; text-align:center; font-family:'Segoe UI';margin-top:8px;">
                <h3 style="margin:2px 0 8px 0;">{zone} {emoji}</h3>
                <h1 style="margin:0 0 6px 0;">{util:.0f}%</h1>
                <p style="margin:0;">In Use: <b>{in_use}</b> | Available: <b>{avail}</b></p>
                <p style="margin:6px 0 0 0;">⏱ ETA: <b>{eta} min</b></p>
            </div>
            """, unsafe_allow_html=True)

            # --- ACTION BUTTONS ---
            c1, c2 = col.columns(2)

            # ✅ CHECK-IN
            if c1.button("✅ Check In", key=f"checkin_{zone}", use_container_width=True):
                r = post_usage_update(zone, "in_use")
                if not r:
                    st.error("Network issue — please try again.")
                elif r.status_code in (200, 201):
                    st.success(f"Checked into {zone}.")
                    st.rerun()
                elif r.status_code == 400 and "already checked into" in r.text:
                    error_msg = r.json().get("detail", "")
                    try:
                        prev_zone = error_msg.split("into ")[1].split(" (")[0]
                    except Exception:
                        prev_zone = "unknown"
                    with st.modal("⚠️ Already Checked In"):
                        st.markdown(f"Looks like you're already checked into **{prev_zone}**.")
                        st.markdown(f"Would you like to **check out of {prev_zone}** and check into **{zone}** instead?")
                        colA, colB = st.columns(2)
                        if colA.button("✅ Yes, switch"):
                            requests.post(f"http://127.0.0.1:8000/checkout/{prev_zone}")
                            r2 = post_usage_update(zone, "in_use")
                            if r2 and r2.status_code in (200, 201):
                                st.success(f"Switched to {zone}.")
                                st.rerun()
                            else:
                                st.error("Something went wrong during the switch.")
                        if colB.button("❌ No, stay"):
                            st.info("Stayed checked into previous zone.")
                else:
                    st.error(f"Update failed ({r.status_code}): {r.text}")

            # 🚪 CHECK-OUT
            if c2.button("🚪 Check Out", key=f"checkout_{zone}", use_container_width=True):
                r = post_usage_update(zone, "available")
                if r and r.status_code in (200, 201):
                    st.success(f"Checked out of {zone}.")
                    st.rerun()

    return clicked

# =====================================================
# DETAIL CHART
# =====================================================
def render_detail(zone: str):
    st.divider()
    st.subheader(f"📈 Detailed Utilization — {zone}")
    logs = fetch_usage_logs(zone)
    if not logs:
        st.info("No usage data yet.")
        return
    ts_df = logs_to_timeseries(logs)
    if ts_df.empty:
        st.info("No plottable timestamps found in logs.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ts_df["ts"], y=ts_df["utilization_percent"], mode="lines+markers", line=dict(width=2), marker=dict(size=6)))
    fig.update_layout(xaxis_title="Time", yaxis_title="Utilization (%)", yaxis=dict(range=[0, 100]), margin=dict(l=10, r=10, t=10, b=10), height=340)
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# MAIN
# =====================================================
data = fetch_heatmap()
if not data:
    st.warning("No data available.")
else:
    zones = data.get("zones", {})
    render_alerts(zones)
    st.divider()
    selected_group = st.selectbox("🎯 Select Muscle Group", list(MUSCLE_ZONE_MAP.keys()), index=0)
    opened = render_zone_cards(data, selected_group)
    if opened:
        render_detail(opened)
