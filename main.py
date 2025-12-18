import os
from fastapi import FastAPI
from pydantic import BaseModel
from google import genai

app = FastAPI()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

class Chat(BaseModel):
    prompt: str

@app.get("/")
def root():
    return {"status": "ONLINE"}

@app.post("/chat")
def chat(data: Chat):
    if not os.getenv("GEMINI_API_KEY"):
        return {"error": "NO GEMINI_API_KEY"}

    res = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=data.prompt
    )
    return {"result": res.text}
