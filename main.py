from fastapi import FastAPI
from routes import equipment
from fastapi.middleware.cors import CORSMiddleware

# =====================================================
# APP INIT
# =====================================================
app = FastAPI(title="UREC Live API")

# =====================================================
# 🔧 Enable CORS for local Streamlit communication
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",   # Streamlit default
        "http://127.0.0.1:8501",   # Alternative
        "*"                        # (Optional) allow all during dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# ROUTES
# =====================================================
app.include_router(equipment.router)

@app.get("/")
def root():
    return {"message": "UREC Live Backend is running with Firebase and CORS enabled!"}
