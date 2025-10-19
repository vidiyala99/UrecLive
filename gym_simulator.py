import threading
import time
import random
from datetime import datetime, timedelta
from firebase_admin import firestore
from firebase_config import db  # Ensure this file has firebase_admin initialized

# ------------------------------------------
# CONFIGURATION
# ------------------------------------------
UPDATE_INTERVAL = 10  # seconds
USERS = ["alex", "mia", "tom", "ryan", "eva", "leo", "nora", "chris", "jen", "sam"]

# Define zones and their typical activity levels (probability of being busy)
ZONE_ACTIVITY = {
    "bench": 0.6,
    "chest_machine": 0.5,
    "back_machine": 0.5,
    "squat_rack": 0.7,
    "shoulder_machine": 0.4,
    "bicep_machine": 0.4,
    "tricep_machine": 0.4,
    "leg_machine": 0.6,
    "quad_machine": 0.5,
    "glute_machine": 0.4,
    "dumbbell_set": 0.8,
    "treadmill": 0.9,
    "stair_master": 0.8,
}

# ------------------------------------------
# UTILITIES
# ------------------------------------------
def random_user():
    return random.choice(USERS)

def update_heatmap():
    """Updates the analytics/heatmap document in Firestore."""
    heatmap_ref = db.collection("analytics").document("heatmap")
    data = heatmap_ref.get().to_dict() or {"zones": {}}
    zones = data.get("zones", {})

    # Iterate through equipment zones
    for zone, base_activity in ZONE_ACTIVITY.items():
        utilization = round(random.uniform(base_activity * 40, base_activity * 100), 1)
        zones[zone] = {
            "utilization_percent": utilization,
            "active_users": int(utilization / 20),
            "last_updated": datetime.now().isoformat(),
        }

    heatmap_ref.set({
        "zones": zones,
        "updated_at": datetime.now().isoformat()
    })
    print(f"📊 Heatmap updated @ {datetime.now().strftime('%H:%M:%S')}")

def simulate_equipment_activity():
    """Simulate users checking in/out on equipment."""
    equip_ref = db.collection("equipments")
    all_equip = [e.to_dict() for e in equip_ref.stream()]
    if not all_equip:
        print("⚠️ No equipment found in Firestore. Did you seed the database?")
        return

    for eq in all_equip:
        zone = eq.get("zone")
        eq_id = eq.get("equipment_id")
        if not zone or not eq_id:
            continue

        doc_ref = equip_ref.document(eq_id)
        activity_prob = ZONE_ACTIVITY.get(zone, 0.5)

        # Simulate check-in
        if eq["status"] == "available" and random.random() < (activity_prob * 0.1):
            user = random_user()
            start_time = datetime.now().isoformat()
            doc_ref.update({
                "status": "in_use",
                "current_user": user,
                "start_time": start_time
            })
            db.collection("usage_logs").add({
                "user": user,
                "equipment_id": eq_id,
                "zone": zone,
                "status": "in_use",
                "start_time": start_time
            })
            print(f"✅ {user} checked into {eq_id} ({zone})")

        # Simulate check-out
        elif eq["status"] == "in_use" and random.random() < (1 - activity_prob) * 0.2:
            duration = random.randint(5, 20)
            user = eq.get("current_user", "")
            start_time = eq.get("start_time") or datetime.now().isoformat()
            end_time = datetime.now().isoformat()

            # Log completion
            db.collection("usage_logs").add({
                "user": user,
                "equipment_id": eq_id,
                "zone": zone,
                "status": "completed",
                "start_time": start_time,
                "end_time": end_time,
                "duration_mins": duration
            })

            # Reset equipment
            doc_ref.update({
                "status": "available",
                "current_user": "",
                "start_time": ""
            })
            print(f"🏁 {user} checked out from {eq_id} after {duration} min")

def run_simulator():
    """Main simulator loop."""
    while True:
        try:
            simulate_equipment_activity()
            update_heatmap()
            print("🔁 Simulation cycle complete.\n")
            time.sleep(UPDATE_INTERVAL)
        except Exception as e:
            print("⚠️ Simulator error:", e)
            time.sleep(UPDATE_INTERVAL)

def start_background_simulator():
    """Launch simulator in background thread."""
    t = threading.Thread(target=run_simulator, daemon=True)
    t.start()
    print("🚀 Gym simulator started in background.")
