from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import json
import uvicorn
from mongodb import users_collection
from typing import Optional, List
from rank_bm25 import BM25Okapi
import re
from string import punctuation

app = FastAPI()

class InputData(BaseModel):
    query: str
    user_ID: str
    context: Optional[List[str]] = None

# Define a simple English stopword list
STOPWORDS = set([
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves',
    'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
    'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
    'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an',
    'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about',
    'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up',
    'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
    'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don',
    'should', 'now'
])

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
    
# Enhanced regex-based tokenizer with stopword and punctuation removal
def simple_tokenize(text, remove_stopwords=True):
    tokens = re.findall(r"\b\w+\b", text.lower())
    if remove_stopwords:
        filtered = [t for t in tokens if t not in STOPWORDS and t not in punctuation]
    else:
        filtered = [t for t in tokens if t not in punctuation]
    return filtered

@app.post("/ask-ai")
def ask_ai(data: InputData):
    try:
        # Fetch a larger window of history
        docs = list(users_collection.find({"user_id": data.user_ID}).sort("_id", -1).limit(50))
        if docs:
            # Prepare documents for BM25
            history_texts = [
                f"{doc.get('user_promt', '')} {doc.get('AI', '')}" for doc in docs
            ]
            tokenized_corpus = [simple_tokenize(text, remove_stopwords=True) for text in history_texts]
            tokenized_query = simple_tokenize(data.query, remove_stopwords=False)
            print("Query:", data.query)
            # print("Tokenized query:", tokenized_query)
            # print("History texts:", history_texts)
            # print("Tokenized corpus:", tokenized_corpus)
            # Check for empty query or empty corpus
            if not tokenized_query or not any(tokenized_corpus):
                history = []
                print("BM25 skipped: empty query or corpus.")
            else:
                bm25 = BM25Okapi(tokenized_corpus)
                scores = bm25.get_scores(tokenized_query)
                top_n = 5
                top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
                # Select the most relevant history
                relevant_docs = [docs[i] for i in top_indices]
                history = []
                for doc in relevant_docs:
                    history.append({
                        "user_prompt": doc.get("user_promt", ""),
                        "AI": doc.get("AI", "")
                    })
                print("Top 5 relevant history loaded from MongoDB using BM25:", history)
        else:
            history = []

        if data.context:
            if isinstance(data.context, list):
                joined_context = "\n\n".join(data.context)
            else:
                joined_context = str(data.context)
            payload = json.dumps({"query": data.query, "context": joined_context, "history": history})
        else:
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
    uvicorn.run(app, host="0.0.0.0", port=8000)