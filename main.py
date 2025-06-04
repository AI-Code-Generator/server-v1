import os
from pyexpat import model
import sys
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import json
from pymongo import MongoClient

app = FastAPI()

class InputData(BaseModel):
    user_id: str
    query: str

# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient("mongodb+srv://trmnteam:tBp54siAioeGkVpb@cluster0.68spx5t.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["chat_db"]
history_collection = db["chat_history"]

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
        result = subprocess.run(
            ['python', 'chat.py', data.user_id, data.query],
            capture_output=True,
            text=True
        )
        response_text = result.stdout.strip()
        error_text = result.stderr.strip()

        # Load existing history
        history = load_history(data.user_id)

        # Append the user's input and the AI's response to the history
        history.append({"role": "user", "parts": [data.query]})
        history.append({"role": "model", "parts": [response_text]})

        # Save the updated history
        save_history(data.user_id, history)

        return {"response": response_text, "error": error_text}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# db connection and other configurations

def load_history(user_id):
    doc = history_collection.find_one({"user_id": user_id})
    if doc and "history" in doc:
        return doc["history"]
    return []

def save_history(user_id, history):
    history_collection.update_one(
        {"user_id": user_id},
        {"$set": {"history": history}},
        upsert=True
    )

if len(sys.argv) > 2:
    user_id = sys.argv[1]
    user_input = sys.argv[2]
    history = load_history(user_id)
    chat_session = model.start_chat(history=history)
    response = chat_session.send_message(user_input)
    history.append({"role": "user", "parts": [user_input]})
    history.append({"role": "model", "parts": [response.text]})
    save_history(user_id, history)
    print(response.text)
else:
    print("Error: No user_id or input provided.")