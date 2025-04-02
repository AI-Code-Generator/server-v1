import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Model configuration
generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Initialize model
model = genai.GenerativeModel(
    model_name="gemini-2.5-pro-exp-03-25",
    safety_settings=safety_settings,
    generation_config=generation_config,
    system_instruction="You are an expert at coding. You are a coding assistant. You are a large language model trained by Google.",
)

# Start a new chat session
chat_session = model.start_chat(history=[])

# Get input from command-line argument
if len(sys.argv) > 1:
    user_input = sys.argv[1]
    response = chat_session.send_message(user_input)
    print(response.text)
else:
    print("Error: No input provided.")
