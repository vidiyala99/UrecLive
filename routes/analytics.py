from fastapi import APIRouter
from firebase_admin import firestore

router = APIRouter(prefix="/analytics", tags=["Analytics"])
db = firestore.client()

@router.get("/heatmap")
def get_heatmap():
    """
    Returns a simple utilization summary per equipment type.
    """
    equipments_ref = db.collection("equipments").stream()
    zone_stats = {}

    for doc in equipments_ref:
        data = doc.to_dict()
        zone = data.get("equipment_type", "unknown")
        status = data.get("status", "available")

        if zone not in zone_stats:
            zone_stats[zone] = {"in_use": 0, "available": 0, "total": 0}

        zone_stats[zone]["total"] += 1
        if status == "in_use":
            zone_stats[zone]["in_use"] += 1
        else:
            zone_stats[zone]["available"] += 1

    # Calculate utilization percentage
    for z, v in zone_stats.items():
        total = v["total"]
        in_use = v["in_use"]
        v["utilization_percent"] = round((in_use / total) * 100, 2) if total > 0 else 0

    return {"zones": zone_stats}
