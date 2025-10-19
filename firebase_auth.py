import os
import requests
from dotenv import load_dotenv

# -----------------------------------------------------
# Load Firebase credentials
# -----------------------------------------------------
load_dotenv()
API_KEY = os.getenv("FIREBASE_API_KEY")

# Firebase REST API endpoints
SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"

# -----------------------------------------------------
# Authentication Helpers
# -----------------------------------------------------
def signup_user(email: str, password: str):
    """Create a new Firebase user account."""
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        r = requests.post(SIGNUP_URL, json=payload)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Signup failed: {r.text if 'r' in locals() else e}")

def signin_user(email: str, password: str):
    """Sign in existing Firebase user."""
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        r = requests.post(SIGNIN_URL, json=payload)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Login failed: {r.text if 'r' in locals() else e}")
