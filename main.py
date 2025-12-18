import os, time, hmac, hashlib
from typing import Dict
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
from collections import defaultdict, deque

# ================= CONFIG =================
APP_NAME = "Ω-NEXUS"
PORT = int(os.getenv("PORT", "10000"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OWNER_TOKEN = os.getenv("LUCIFER", "LUCIFER_666")

if not GEMINI_KEY:
    print("⚠️ GEMINI_API_KEY NOT SET")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ================= FASTAPI =================
app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= RATE LIMIT (FREE SAFE) =========
RATE_LIMIT = 10          # 10 req
WINDOW = 60              # ต่อ 60 วิ
rate_map = defaultdict(deque)

def rate_guard(ip: str):
    now = time.time()
    q = rate_map[ip]
    while q and now - q[0] > WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "RATE LIMITED")
    q.append(now)

# ================= MEMORY =================
persona_memory: Dict[str, dict] = {}
MEM_LIMIT = 10

# ================= MODELS =================
class ChatRequest(BaseModel):
    prompt: str
    user_id: str = "guest"

# ================= ROUTES =================
@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>Ω‑NEXUS ONLINE</h1>"

@app.get("/health")
def health():
    return {
        "status": "ONLINE",
        "users": len(persona_memory)
    }

@app.post("/chat")
def chat(data: ChatRequest, request: Request):
    rate_guard(request.client.host)

    uid = data.user_id.strip() or "guest"
    mem = persona_memory.setdefault(uid, [])
    mem.append(data.prompt)
    if len(mem) > MEM_LIMIT:
        mem[:] = mem[-MEM_LIMIT:]

    prompt = f"""
คุณคือ Ω‑NEXUS AI
ตอบสั้น ชัด ใช้งานได้จริง

Context:
{mem}

User:
{data.prompt}
"""

    try:
        resp = model.generate_content(prompt)
        text = resp.text if resp and resp.text else "⚠️ AI ไม่ตอบ"
    except Exception as e:
        text = f"⚠️ GEMINI ERROR: {str(e)}"

    return {"result": text}

# ================= ADMIN =================
@app.get("/admin/memory")
def admin_mem(authorization: str = Header(None)):
    if authorization != OWNER_TOKEN:
        raise HTTPException(403, "FORBIDDEN")
    return persona_memory

# ================= START =================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
