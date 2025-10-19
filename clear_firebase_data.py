import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# List of collections to clear
collections_to_clear = [
    "equipments",
    "exercises",
    "usage_logs",
    "analytics"
]

def clear_collection(collection_name):
    print(f"🧹 Clearing collection: {collection_name}")
    docs = db.collection(collection_name).stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    print(f"✅ Deleted {count} documents from {collection_name}\n")

if __name__ == "__main__":
    for c in collections_to_clear:
        clear_collection(c)
    print("🎯 All selected collections cleared successfully!")
