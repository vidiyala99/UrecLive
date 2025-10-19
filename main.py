from fastapi import FastAPI
from routes import equipment, exercises, analytics
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="UREC Live API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(equipment.router)
app.include_router(exercises.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {"message": "UREC Live Backend running with Firebase and CORS enabled!"}
