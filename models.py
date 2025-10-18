from pydantic import BaseModel

class Equipment(BaseModel):
    equipment_id: str
    name: str
    zone: str
    status: str
    avg_duration: int
    current_user: str | None = None
    start_time: str | None = None
