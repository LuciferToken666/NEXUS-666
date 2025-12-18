import os
from fastapi import FastAPI
from pydantic import BaseModel
from google import genai

# ===== ENV =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY NOT SET")

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

class Chat(BaseModel):
    prompt: str

@app.get("/")
def root():
    return {"status": "OMEGA ONLINE"}

@app.post("/chat")
def chat(data: Chat):
    resp = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=data.prompt
    )
    return {"result": resp.text}
