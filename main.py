from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()

class InputData(BaseModel):
    query: str  # Update the model to include 'query'

@app.get("/")
def read_root():
    return {"message": "Hello, world!"}

@app.get("/run-script")
def run_script():
    try:
        # Run the chat.py script
        result = subprocess.run(
            ['python', 'chat.py'],  # Ensure 'python' points to the correct Python interpreter
            capture_output=True,
            text=True
        )
        return {
            "output": result.stdout,  # Output from the script
            "error": result.stderr    # Any errors from the script
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/ask-ai")
def ask_ai(data: InputData):
    try:
        # Run chat.py with the user's query as an argument
        result = subprocess.run(['python', 'chat.py', data.query], capture_output=True, text=True)
        
        # Return AI response
        return {"response": result.stdout.strip(), "error": result.stderr.strip()}
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)