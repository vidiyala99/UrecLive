from fastapi import APIRouter, HTTPException
from firebase_config import db
from models import Equipment
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

# =====================================================
# 🟢 1. Fetch all equipments
# =====================================================
@router.get("/equipments")
def get_all_equipment():
    equipments_ref = db.collection("equipments")
    docs = equipments_ref.stream()
    return [doc.to_dict() for doc in docs]


# =====================================================
# 🟡 2. Add new equipment
# =====================================================
@router.post("/equipments")
def add_equipment(equipment: Equipment):
    doc_ref = db.collection("equipments").document(equipment.equipment_id)
    doc_ref.set(equipment.dict())
    return {"message": "Equipment added successfully", "equipment_id": equipment.equipment_id}


# =====================================================
# 🔵 3. Update existing equipment (manual patch)
# =====================================================
@router.patch("/equipments/{equipment_id}")
def update_equipment(equipment_id: str, data: dict):
    doc_ref = db.collection("equipments").document(equipment_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Equipment not found")
    doc_ref.update(data)
    return {"message": f"Equipment {equipment_id} updated", "updated_fields": data}


# =====================================================
# ✅ 4. Check-in (ZONE-AWARE + ONE-SESSION-PER-USER)
# =====================================================
@router.post("/checkin/{zone_name}")
def check_in(zone_name: str, user: str = "demo_user"):
    """
    Allows a user to check in only if they are not already using another equipment.
    Finds the first available equipment within the given zone and marks it in use.
    """
    # Step 1️⃣ — Prevent duplicate check-ins
    active_ref = db.collection("equipments").where("current_user", "==", user).where("status", "==", "in_use").stream()
    for d in active_ref:
        active_data = d.to_dict()
        raise HTTPException(
            status_code=400,
            detail=f"User '{user}' is already checked into {active_data.get('zone')} "
                   f"({active_data.get('equipment_id')}). Please check out first."
        )

    # Step 2️⃣ — Proceed with normal check-in
    equipments_ref = db.collection("equipments")
    docs = equipments_ref.where("zone", "==", zone_name).where("status", "==", "available").stream()

    target = None
    for d in docs:
        target = d
        break

    if not target:
        raise HTTPException(status_code=404, detail=f"No available equipment found in zone '{zone_name}'")

    doc_ref = db.collection("equipments").document(target.id)
    start_time = datetime.utcnow().isoformat()

    doc_ref.update({
        "status": "in_use",
        "current_user": user,
        "start_time": start_time
    })

    return {
        "message": f"{target.id} checked in under zone '{zone_name}' by {user}",
        "equipment_id": target.id,
        "start_time": start_time
    }


# =====================================================
# 🔵 5. Check-out (ZONE-AWARE)
# =====================================================
@router.post("/checkout/{zone_name}")
def check_out(zone_name: str):
    """
    Find the first 'in_use' equipment within the given zone and mark it available.
    """
    equipments_ref = db.collection("equipments")
    docs = equipments_ref.where("zone", "==", zone_name).where("status", "==", "in_use").stream()

    target = None
    for d in docs:
        target = d
        break

    if not target:
        raise HTTPException(status_code=404, detail=f"No in-use equipment found in zone '{zone_name}'")

    data = target.to_dict()
    doc_ref = db.collection("equipments").document(target.id)

    # Calculate duration
    start_time_str = data.get("start_time")
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
        duration = (datetime.utcnow() - start_time).seconds // 60
    else:
        duration = 0

    # Save usage log
    log_id = f"{target.id}_{datetime.utcnow().isoformat()}"
    db.collection("usage_logs").document(log_id).set({
        "equipment_id": target.id,
        "zone": zone_name,
        "user": data.get("current_user", ""),
        "start_time": start_time_str,
        "end_time": datetime.utcnow().isoformat(),
        "duration": duration
    })

    # Update equipment back to available
    doc_ref.update({
        "status": "available",
        "current_user": "",
        "start_time": ""
    })

    # Recalculate average duration
    logs_ref = db.collection("usage_logs").where("equipment_id", "==", target.id)
    logs = logs_ref.stream()
    durations = [log.to_dict().get("duration", 0) for log in logs if log.to_dict().get("duration")]

    if durations:
        new_avg = round(sum(durations) / len(durations))
        doc_ref.update({"avg_duration": new_avg})
    else:
        new_avg = "Not enough data yet"

    return {
        "message": f"{target.id} checked out from zone '{zone_name}', duration {duration} minutes",
        "equipment_id": target.id,
        "new_avg_duration": new_avg
    }


# =====================================================
# 📊 6. Get usage logs for a specific equipment
# =====================================================
@router.get("/usage_logs/{equipment_id}")
def get_usage_logs(equipment_id: str):
    logs_ref = db.collection("usage_logs").where("equipment_id", "==", equipment_id)
    logs = logs_ref.stream()

    log_list = [log.to_dict() for log in logs]
    log_list.sort(key=lambda x: x.get("end_time", ""), reverse=True)

    return {
        "equipment_id": equipment_id,
        "total_sessions": len(log_list),
        "logs": log_list
    }


# =====================================================
# 🧩 7. Streamlit compatibility model
# =====================================================
class UsageUpdateRequest(BaseModel):
    zone: str
    status: str  # "in_use" or "available"
    user: str = "demo_user"
    timestamp: datetime


# =====================================================
# 🔥 8. Streamlit compatibility endpoint
# =====================================================
@router.post("/usage_logs/update")
def update_usage_log(req: UsageUpdateRequest):
    """
    Compatibility endpoint for Streamlit dashboard.
    Automatically triggers checkin/checkout logic per zone.
    """
    if not req.zone or not req.status:
        raise HTTPException(status_code=400, detail="Missing 'zone' or 'status' field")

    zone = req.zone.strip()
    user = req.user.strip() or "demo_user"

    if req.status == "in_use":
        return check_in(zone, user)
    elif req.status == "available":
        return check_out(zone)
    else:
        raise HTTPException(status_code=400, detail="Invalid status value")


# =====================================================
# 🔥 9. Analytics Heatmap
# =====================================================
@router.get("/analytics/heatmap")
def get_heatmap():
    """
    Returns live utilization stats grouped by gym zone.
    """
    equipments_ref = db.collection("equipments")
    docs = equipments_ref.stream()

    zone_data = {}

    for doc in docs:
        data = doc.to_dict()
        zone = data.get("zone", "Unknown")
        status = data.get("status", "available")

        if zone not in zone_data:
            zone_data[zone] = {"available": 0, "in_use": 0}

        if status == "in_use":
            zone_data[zone]["in_use"] += 1
        else:
            zone_data[zone]["available"] += 1

    for zone, stats in zone_data.items():
        total = stats["available"] + stats["in_use"]
        utilization = (stats["in_use"] / total * 100) if total > 0 else 0
        zone_data[zone]["utilization_percent"] = round(utilization, 1)

    return {"zones": zone_data}
