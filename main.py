from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import pymongo
import json

app = FastAPI()

class InputData(BaseModel):
    query: str
    user_ID: str

try:
    client = pymongo.MongoClient("mongodb+srv://trmnteam:tBp54siAioeGkVpb@cluster0.68spx5t.mongodb.net/", serverSelectionTimeoutMS=3000)
    # This will throw an exception if not connected
    client.admin.command('ping')
    print("MongoDB connection: SUCCESS")
except Exception as e:
    print(f"MongoDB connection: FAILED ({e})")

# Connect to MongoDB (adjust the connection string as needed)
client = pymongo.MongoClient("mongodb+srv://trmnteam:tBp54siAioeGkVpb@cluster0.68spx5t.mongodb.net/")
db = client["CODE_GENERATOR"]
users_collection = db["users"]

@app.get("/")
def read_root():
    return {"message": "Hello, world!"}

@app.get("/run-script")
def run_script():
    try:
        # Run the chat.py script
        result = subprocess.run(
            ['python', 'chat.py'],
            capture_output=True,
            text=True
        )
        return {
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/ask-ai")
def ask_ai(data: InputData):
    try:
        # Retrieve the latest document for the user with user_id data.user_ID
        docs = list(users_collection.find({"user_id": data.user_ID}))

        # Build history from all retrieved documents; if none found, use an empty list
        if docs:
            history = []
            for doc in docs:
                history.append({
                    "user_prompt": doc.get("user_promt", ""),
                    "AI": doc.get("AI", "")
                })
            print("History loaded from MongoDB:", history)
        else:
            history = []
        payload = json.dumps({"query": data.query, "history": history})
        result = subprocess.run(
            ['python', 'chat.py', payload],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            users_collection.insert_one({
            "user_id": data.user_ID,
            "user_promt": data.query,
            "AI": result.stdout.strip()
            })
        return {"response": result.stdout.strip(), "error": result.stderr.strip()}
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)