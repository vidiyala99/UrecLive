import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase app (use your service account key)
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Create a Firestore client
db = firestore.client()
