from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import json
from mongodb import users_collection

app = FastAPI()

class InputData(BaseModel):
    query: str
    user_ID: str

@app.get("/")
def read_root():
    return {"message": "Hello, world!"}

@app.get("/run-script")
def run_script():
    try:
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
        docs = list(users_collection.find({"user_id": data.user_ID}))
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