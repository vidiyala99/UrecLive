import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random

# Initialize Firebase
# Make sure the serviceAccountKey.json file is in the same directory
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
except ValueError:
    print("Firebase app already initialized.")
db = firestore.client()


# ----------------------------------------------------
# EQUIPMENT CONFIG
# ----------------------------------------------------
EQUIPMENT_ZONES = {
    "bench": 12,
    "chest_machine": 8,
    "back_machine": 8,
    "squat_rack": 12,
    "shoulder_machine": 5,
    "bicep_machine": 5,
    "tricep_machine": 5,
    "leg_machine": 8,
    "quad_machine": 8,
    "glute_machine": 8,
    "dumbbell_set": 2,
    "cable_station": 6,  # <-- ADDED
    "treadmill": 20,
    "stair_master": 20,
}

EXERCISES = {
    "Chest": [
        ("Flat Barbell Bench Press", "bench"),
        ("Incline Dumbbell Press", "bench"),
        ("Cable Fly", "chest_machine"),
        ("Chest Press", "chest_machine"),
    ],
    "Back": [
        ("Lat Pulldown", "back_machine"),
        ("Seated Row", "back_machine"),
        ("T-Bar Row", "squat_rack"),
        ("Pull-Up", "bench"),
    ],
    "Shoulders": [
        ("Shoulder Press", "shoulder_machine"),
        ("Lateral Raise", "dumbbell_set"),
        ("Rear Delt Fly", "shoulder_machine"),
    ],
    "Biceps": [
        ("Barbell Curl", "bicep_machine"),
        ("Preacher Curl", "bicep_machine"),
        ("Cable Curl", "cable_station"),  # <-- CORRECTED
        ("Hammer Curl", "dumbbell_set"),
    ],
    "Triceps": [
        ("Rope Pushdown", "tricep_machine"),
        ("Skull Crusher", "bench"),
        ("Dips", "bench"),
    ],
    "Legs": [
        ("Leg Press", "leg_machine"),
        ("Leg Curl", "leg_machine"),
    ],
    "Quads": [
        ("Hack Squat", "quad_machine"),
        ("Leg Extension", "quad_machine"),
        ("Split Squat", "squat_rack"),
    ],
    "Glutes": [
        ("Hip Thrust", "glute_machine"),
        ("Glute Kickback", "glute_machine"),
        ("Bulgarian Split Squat", "bench"),
    ],
    "Calves": [
        ("Calf Raise", "leg_machine"),
    ],
    "Cardio": [
        ("Treadmill Run", "treadmill"),
        ("Stair Climb", "stair_master"),
        ("Incline Walk", "treadmill"),
    ],
}

USERS = ["alex", "mia", "tom", "ryan", "eva", "leo", "nora", "chris", "jen", "sam"]

# ----------------------------------------------------
# SEED EQUIPMENTS
# ----------------------------------------------------
print("⏳ Seeding equipments...")
equip_ref = db.collection("equipments")
equip_ref_list = []

for zone, count in EQUIPMENT_ZONES.items():
    for i in range(1, count + 1):
        eq_id = f"{zone}_{i:02d}"
        status = random.choice(["available", "in_use"])
        current_user = random.choice(USERS) if status == "in_use" else ""
        start_time = (
            datetime.now() - timedelta(minutes=random.randint(5, 40))
        ).isoformat() if current_user else ""
        data = {
            "equipment_id": eq_id,
            "zone": zone,
            "equipment_type": zone,
            "status": status,
            "current_user": current_user,
            "start_time": start_time,
            "avg_duration": random.randint(10, 25),
            "usage_count": random.randint(10, 100)
        }
        equip_ref.document(eq_id).set(data)
        equip_ref_list.append(eq_id)

print(f"✅ {len(equip_ref_list)} equipments added.")

# ----------------------------------------------------
# SEED EXERCISES
# ----------------------------------------------------
print("⏳ Seeding exercises...")
ex_ref = db.collection("exercises")
for muscle, exs in EXERCISES.items():
    for ex, eq_type in exs:
        ex_ref.document(ex).set({
            "exercise_name": ex,
            "primary_muscle": muscle,
            "equipment_type": eq_type,
            "recommended_sets": random.randint(3, 5),
            "recommended_reps": random.choice([8, 10, 12]),
            "avg_duration": random.randint(10, 20)
        })
print(f"✅ {sum(len(v) for v in EXERCISES.values())} exercises added.")

# ----------------------------------------------------
# SEED USER ACTIVITY LOGS
# ----------------------------------------------------
print("⏳ Seeding usage logs...")
logs_ref = db.collection("usage_logs")
for _ in range(200):
    user = random.choice(USERS)
    eq = random.choice(equip_ref_list)
    zone = eq.split("_")[0]
    exercise = random.choice(random.choice(list(EXERCISES.values())))[0]
    start = datetime.now() - timedelta(minutes=random.randint(10, 90))
    duration = random.randint(8, 25)
    end = start + timedelta(minutes=duration)

    logs_ref.add({
        "user": user,
        "exercise": exercise,
        "equipment_id": eq,
        "zone": zone,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "duration_mins": duration,
        "status": "completed"
    })

print("✅ 200 user workout logs added.")
print("🎉 Firebase seeding complete!")

