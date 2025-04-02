from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()

class InputData(BaseModel):
    query: str

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
        result = subprocess.run(['python', 'chat.py', data.query], capture_output=True, text=True)
        
        return {"response": result.stdout.strip(), "error": result.stderr.strip()}
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)