from firebase_config import db
from datetime import datetime

# =====================================================
# Mock Equipment Data
# =====================================================
mock_equipments = [
    {"equipment_id": "bench_1", "zone": "benches", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "bench_2", "zone": "benches", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "dumbbell_1", "zone": "dumbbells", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "dumbbell_2", "zone": "dumbbells", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "squat_1", "zone": "squat racks", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "squat_2", "zone": "squat racks", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "back_1", "zone": "Back Machines", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "back_2", "zone": "Back Machines", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "cardio_1", "zone": "cardio", "status": "available", "current_user": "", "start_time": ""},
    {"equipment_id": "cardio_2", "zone": "cardio", "status": "available", "current_user": "", "start_time": ""},
]

# =====================================================
# Push to Firestore
# =====================================================
def seed_equipments():
    print("🔥 Seeding mock gym equipments into Firebase...")
    for eq in mock_equipments:
        db.collection("equipments").document(eq["equipment_id"]).set(eq)
        print(f"✅ Added {eq['equipment_id']} in {eq['zone']}")
    print("🎉 All mock equipments added successfully!")

if __name__ == "__main__":
    seed_equipments()
