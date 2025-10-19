from fastapi import APIRouter
from firebase_admin import firestore

router = APIRouter(prefix="/exercises", tags=["Exercises"])
db = firestore.client()

@router.get("/")
def get_exercises():
    """
    Fetch all exercises from Firestore collection 'exercises'
    """
    exercises_ref = db.collection("exercises").stream()
    exercises = []
    for doc in exercises_ref:
        data = doc.to_dict()
        exercises.append({
            "exercise_name": data.get("exercise_name"),
            "primary_muscle": data.get("primary_muscle"),
            "equipment_type": data.get("equipment_type"),
            "avg_duration": data.get("avg_duration", 10),
            "recommended_sets": data.get("recommended_sets", 3),
            "recommended_reps": data.get("recommended_reps", 8),
        })
    return {"exercises": exercises}
