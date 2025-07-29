from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import json
import uvicorn
from typing import Optional, List
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class InputData(BaseModel):
    query: str
    user_ID: str
    context: Optional[List[str]] = None

# Load SentenceTransformer model globally
embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Initialize Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "conversation-history")

# Initialize Pinecone with new API
pc = Pinecone(api_key=PINECONE_API_KEY)

# Get or create index
try:
    index = pc.Index(PINECONE_INDEX_NAME)
    print(f"Connected to Pinecone index: {PINECONE_INDEX_NAME}")
except Exception as e:
    print(f"Error connecting to Pinecone: {e}")
    print("Please check your Pinecone API key and run setup_pinecone.py first")

def store_conversation_vector(user_id, user_prompt, ai_response, conversation_id):
    """Store conversation in Pinecone vector database using user namespace"""
    try:
        text = f"{user_prompt} {ai_response}"
        embedding = embedder.encode([text])[0].tolist()
        
        # Store in user's namespace
        index.upsert(
            vectors=[{
                'id': conversation_id,  # No need for user_id prefix in namespace
                'values': embedding,
                'metadata': {
                    'user_prompt': user_prompt,
                    'ai_response': ai_response,
                    'timestamp': datetime.now().isoformat()
                }
            }],
            namespace=user_id  # Each user gets their own namespace
        )
        print(f"Stored conversation vector for user {user_id} in namespace {user_id}")
        return True
    except Exception as e:
        print(f"Error storing conversation vector: {e}")
        return False

def search_user_conversations(user_id, query, top_k=10):
    """Search for relevant conversations in user's namespace"""
    try:
        query_embedding = embedder.encode([query])[0].tolist()
        
        # Search in user's namespace
        results = index.query(
            vector=query_embedding,
            namespace=user_id,  # Search only in user's namespace
            top_k=top_k,
            include_metadata=True
        )
        
        return results.matches
    except Exception as e:
        print(f"Error searching conversations for user {user_id}: {e}")
        return []

def check_duplicate_conversation(user_id, user_prompt, ai_response):
    """Check if exact conversation already exists in user's namespace"""
    try:
        # Search for exact match in user's namespace
        results = index.query(
            vector=embedder.encode([f"{user_prompt} {ai_response}"])[0].tolist(),
            namespace=user_id,  # Search only in user's namespace
            filter={
                "user_prompt": user_prompt,
                "ai_response": ai_response
            },
            top_k=1,
            include_metadata=True
        )
        
        return len(results.matches) > 0
    except Exception as e:
        print(f"Error checking duplicate for user {user_id}: {e}")
        return False

def get_user_conversation_stats(user_id):
    """Get statistics for a user's namespace"""
    try:
        stats = index.describe_index_stats(filter={"user_id": user_id})
        return stats
    except Exception as e:
        print(f"Error getting stats for user {user_id}: {e}")
        return None

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

@app.get("/user-stats/{user_id}")
def get_user_stats(user_id: str):
    """Get conversation statistics for a specific user"""
    try:
        stats = get_user_conversation_stats(user_id)
        if stats:
            return {
                "user_id": user_id,
                "total_conversations": stats.total_vector_count,
                "namespace": user_id
            }
        else:
            return {"user_id": user_id, "total_conversations": 0, "namespace": user_id}
    except Exception as e:
        return {"error": str(e)}

@app.post("/ask-ai")
def ask_ai(data: InputData):
    try:
        # 1. Search Pinecone for relevant history in user's namespace
        vector_results = search_user_conversations(data.user_ID, data.query, top_k=10)
        
        # 2. Extract history from vector results
        history = []
        if vector_results:
            history = [
                {
                    "user_prompt": result.metadata['user_prompt'],
                    "AI": result.metadata['ai_response']
                }
                for result in vector_results
            ]
            print(f"Found {len(history)} relevant conversations from user {data.user_ID}'s namespace")

        # 3. Prepare payload
        if data.context:
            if isinstance(data.context, list):
                joined_context = "\n\n".join(data.context)
            else:
                joined_context = str(data.context)
            payload = json.dumps({"query": data.query, "context": joined_context, "history": history})
        else:
            payload = json.dumps({"query": data.query, "history": history})
        
        # 4. Generate AI response
        result = subprocess.run(
            ['python', 'chat.py', payload],
            capture_output=True,
            text=True
        )
        
        ai_response = result.stdout.strip()
        
        # 5. Store in Pinecone if response exists
        if ai_response:
            # Check for duplicate before storing
            is_duplicate = check_duplicate_conversation(data.user_ID, data.query, ai_response)
            
            if not is_duplicate:
                # Store new conversation in user's namespace
                conversation_id = str(uuid.uuid4())
                store_success = store_conversation_vector(data.user_ID, data.query, ai_response, conversation_id)
                
                if store_success:
                    print(f"New conversation stored for user {data.user_ID} in namespace {data.user_ID}")
                else:
                    print(f"Failed to store conversation for user {data.user_ID}")
            else:
                print(f"Duplicate conversation found for user {data.user_ID}, skipping store")
        
        return {"response": ai_response, "error": result.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
