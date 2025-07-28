from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import json
import uvicorn
from mongodb import users_collection
from typing import Optional, List
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI()

class InputData(BaseModel):
    query: str
    user_ID: str
    context: Optional[List[str]] = None

# Load SentenceTransformer model globally
embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

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

# Function to retrieve top N similar documents based on embeddings
def get_most_relevant_history(query, history_texts, top_n=5):
    query_embedding = embedder.encode([query])
    history_embeddings = embedder.encode(history_texts)
    similarities = cosine_similarity(query_embedding, history_embeddings)[0]
    top_indices = similarities.argsort()[-top_n:][::-1]
    return top_indices

@app.post("/ask-ai")
def ask_ai(data: InputData):
    try:
        docs = list(users_collection.find({"user_id": data.user_ID}).sort("_id", -1).limit(50))
        # print("Docs:", docs)
        if docs:
            history_texts = [
                f"{doc.get('user_promt', '')} {doc.get('AI', '')}" for doc in docs
            ]
            if history_texts:
                top_indices = get_most_relevant_history(data.query, history_texts, top_n=10)
                relevant_docs = [docs[i] for i in top_indices]
                history = [
                    {"user_prompt": doc.get("user_promt", ""), "AI": doc.get("AI", "")}
                    for doc in relevant_docs
                ]
                print("Top 10 relevant history loaded from MongoDB using embeddings:", history)
            else:
                history = []
        else:
            history = []

        if data.context:
            if isinstance(data.context, list):
                joined_context = "\n\n".join(data.context)
            else:
                joined_context = str(data.context)
            payload = json.dumps({"query": data.query, "context": joined_context, "history": history})
            # print("Payload with context:", payload)
        else:
            payload = json.dumps({"query": data.query, "history": history})
            # print("Payload without context:", payload)
        
        result = subprocess.run(
            ['python', 'chat.py', payload],
            capture_output=True,
            text=True
        )
        
        ai_response = result.stdout.strip()
        
        # Check if this conversation already exists and update with latest data
        if ai_response:
            existing_doc = users_collection.find_one({
                "user_id": data.user_ID,
                "user_promt": data.query
            })
            
            if existing_doc:
                # Delete ALL previous documents with the same query for this user
                delete_result = users_collection.delete_many({
                    "user_id": data.user_ID,
                    "user_promt": data.query
                })
                print(f"Deleted {delete_result.deleted_count} previous conversations for user {data.user_ID}")
            
            # Insert the new conversation (whether it was a duplicate or not)
            users_collection.insert_one({
                "user_id": data.user_ID,
                "user_promt": data.query,
                "AI": ai_response
            })
            print(f"Conversation stored for user {data.user_ID}")
        
        return {"response": ai_response, "error": result.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
