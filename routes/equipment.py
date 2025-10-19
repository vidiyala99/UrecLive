from fastapi import APIRouter, HTTPException
from firebase_config import db
from models import Equipment
from datetime import datetime

router = APIRouter()

# =====================================================
# 1. Get all equipment
# =====================================================
@router.get("/equipments")
def get_all_equipment():
    docs = db.collection("equipments").stream()
    return [doc.to_dict() for doc in docs]

# =====================================================
# 2. Add new equipment
# =====================================================
@router.post("/equipments")
def add_equipment(equipment: Equipment):
    db.collection("equipments").document(equipment.equipment_id).set(equipment.dict())
    return {"message": "Equipment added successfully", "equipment_id": equipment.equipment_id}

# =====================================================
# 3. Update equipment
# =====================================================
@router.patch("/equipments/{equipment_id}")
def update_equipment(equipment_id: str, data: dict):
    doc_ref = db.collection("equipments").document(equipment_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Equipment not found")
    doc_ref.update(data)
    return {"message": f"Equipment {equipment_id} updated", "updated_fields": data}

# =====================================================
# 4. Check In
# =====================================================
@router.post("/checkin/{zone_name}")
def check_in(zone_name: str, user: str = "demo_user"):
    active_ref = db.collection("equipments").where("current_user", "==", user).where("status", "==", "in_use").stream()
    for d in active_ref:
        existing = d.to_dict()
        raise HTTPException(
            status_code=400,
            detail=f"User '{user}' already checked into {existing.get('zone')} ({existing.get('equipment_id')})"
        )

    docs = db.collection("equipments").where("zone", "==", zone_name).where("status", "==", "available").stream()
    target = next(docs, None)
    if not target:
        raise HTTPException(status_code=404, detail=f"No available equipment found in '{zone_name}'")

    doc_ref = db.collection("equipments").document(target.id)
    start_time = datetime.utcnow().isoformat()
    doc_ref.update({"status": "in_use", "current_user": user, "start_time": start_time})

    return {"message": f"{target.id} checked in under {zone_name} by {user}", "start_time": start_time}

# =====================================================
# 5. Check Out
# =====================================================
@router.post("/checkout/{zone_name}")
def check_out(zone_name: str, user: str):
    # The query now also checks for the correct user
    docs = db.collection("equipments").where("zone", "==", zone_name).where("status", "==", "in_use").where("current_user", "==", user).stream()
    target = next(docs, None)
    if not target:
        # More specific error message
        raise HTTPException(status_code=404, detail=f"User '{user}' not found in any in-use equipment in '{zone_name}'")

    data = target.to_dict()
    doc_ref = db.collection("equipments").document(target.id)
    start_time = datetime.fromisoformat(data.get("start_time")) if data.get("start_time") else datetime.utcnow()
    duration = (datetime.utcnow() - start_time).seconds // 60

    db.collection("usage_logs").add({
        "equipment_id": target.id,
        "zone": zone_name,
        "user": data.get("current_user", ""),
        "start_time": data.get("start_time"),
        "end_time": datetime.utcnow().isoformat(),
        "duration": duration
    })

    doc_ref.update({"status": "available", "current_user": "", "start_time": ""})
    return {"message": f"{target.id} checked out from {zone_name}, duration {duration} mins"}

# =====================================================
# 6. Get Usage Logs
# =====================================================
@router.get("/usage_logs/{equipment_id}")
def get_usage_logs(equipment_id: str):
    logs = db.collection("usage_logs").where("equipment_id", "==", equipment_id).stream()
    result = [log.to_dict() for log in logs]
    result.sort(key=lambda x: x.get("end_time", ""), reverse=True)
    return {"equipment_id": equipment_id, "total_sessions": len(result), "logs": result}

# =====================================================
# 7. Streamlit Compatibility Endpoint
# =====================================================
@router.post("/usage_logs/update")
def update_usage_log(payload: dict):
    print("🔥 Incoming payload:", payload)
    zone = payload.get("zone")
    status = payload.get("status")
    user = payload.get("user", "demo_user")

    if not zone or not status:
        raise HTTPException(status_code=400, detail="Missing 'zone' or 'status'")

    try:
        if status == "in_use":
            return check_in(zone, user)
        else:
            # Pass the 'user' variable to the check_out function
            return check_out(zone, user)
    except HTTPException as e:
        print("⚠️ HTTP Exception:", e.detail)
        raise
    except Exception as e:
        print("💥 General Exception:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 8. Analytics Heatmap
# =====================================================
@router.get("/analytics/heatmap")
def get_heatmap():
    docs = db.collection("equipments").stream()
    zones = {}
    for doc in docs:
        data = doc.to_dict()
        zone = data.get("zone", "Unknown")
        status = data.get("status", "available")
        if zone not in zones:
            zones[zone] = {"available": 0, "in_use": 0}
        if status == "in_use":
            zones[zone]["in_use"] += 1
        else:
            zones[zone]["available"] += 1
            
    for zone, v in zones.items():
        total = v["available"] + v["in_use"]
        v["total"] = total # <-- THIS IS THE FIX
        v["utilization_percent"] = round((v["in_use"] / total) * 100 if total else 0, 1)
        
    return {"zones": zones}

