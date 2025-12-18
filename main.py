import os, time, json, hmac, hashlib
from typing import Dict
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# ================= BASIC CONFIG =================
APP_NAME = "OMEGA-NEXUS-GEMINI"
PORT = int(os.getenv("PORT", "10000"))

GEMINI_API_KEY = os.getenv("GEMINI")
OWNER_TOKEN = os.getenv("LUCIFER")
GUMROAD_SECRET = os.getenv("GUMROAD_SECRET", "")

if not GEMINI_API_KEY:
    print("❌ GEMINI API KEY NOT SET")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ================= FASTAPI ======================
app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= STORAGE ======================
persona_memory: Dict[str, dict] = {}
user_plans: Dict[str, dict] = {}
audit_log = []

MEMORY_DECAY = 60 * 60 * 24  # 24 ชม.

# ================= UTILS ========================
def now():
    return int(time.time())

def log(event: str, detail: dict):
    audit_log.append({"t": now(), "event": event, "detail": detail})
    if len(audit_log) > 1000:
        audit_log.pop(0)

def decay_memory():
    dead = [
        u for u, d in persona_memory.items()
        if now() - d["last"] > MEMORY_DECAY
    ]
    for u in dead:
        persona_memory.pop(u, None)

def owner_guard(token: str):
    if token != OWNER_TOKEN:
        raise HTTPException(status_code=403, detail="OWNER ONLY")

# ================= MODELS =======================
class ChatRequest(BaseModel):
    prompt: str
    user_id: str = "guest"

# ================= ROUTES =======================
@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>Ω OMEGA‑NEXUS (Gemini) ONLINE</h1>"

@app.get("/health")
def health():
    return {
        "status": "ONLINE",
        "users": len(persona_memory),
        "plans": len(user_plans),
    }

# ================= CHAT =========================
@app.post("/chat")
def chat(data: ChatRequest):
    if not GEMINI_API_KEY:
        return {"result": "❌ GEMINI API KEY NOT FOUND"}

    decay_memory()

    uid = data.user_id.strip() or "guest"

    # ---- PLAN CHECK ----
    plan = user_plans.get(uid)
    if plan:
        if now() > plan["expires"]:
            return {"result": "แพ็กเกจหมดอายุ"}
        if plan["quota"] <= 0:
            return {"result": "โควต้าหมด"}
        plan["quota"] -= 1

    # ---- MEMORY ----
    mem = persona_memory.setdefault(uid, {"msgs": [], "last": now()})
    mem["last"] = now()
    mem["msgs"].append(data.prompt)
    mem["msgs"] = mem["msgs"][-20:]

    instruction = "คุณคือ OMEGA AI ตอบชัด กระชับ สุภาพ ไม่เพ้อ"
    prompt = f"{instruction}\nคำสั่ง: {data.prompt}"

    try:
        resp = model.generate_content(prompt)
        result = resp.text if resp.text else "⚠️ ไม่สามารถตอบได้"
    except Exception as e:
        result = f"⚠️ GEMINI ERROR: {str(e)}"

    log("CHAT", {"user": uid})
    return {"result": result}

# ================= GUMROAD ======================
def verify_gumroad(payload: bytes, signature: str) -> bool:
    if not GUMROAD_SECRET or not signature:
        return False
    expected = hmac.new(
        GUMROAD_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/webhook/gumroad")
async def gumroad(request: Request):
    raw = await request.body()
    sig = request.headers.get("X-Gumroad-Signature")

    if not verify_gumroad(raw, sig):
        raise HTTPException(status_code=403, detail="INVALID SIGNATURE")

    form = dict(await request.form())
    email = form.get("email")
    product = form.get("product_name", "").upper()

    if not email:
        return {"status": "IGNORED"}

    if "VIP" in product:
        quota, days = 999999, 30
    elif "PRO" in product:
        quota, days = 300, 30
    else:
        quota, days = 50, 7

    user_plans[email] = {
        "plan": product,
        "quota": quota,
        "expires": now() + days * 86400
    }

    log("SALE", {"email": email, "product": product})
    return {"status": "OK"}

# ================= ADMIN ========================
@app.get("/admin/audit")
def admin_audit(authorization: str = Header(None)):
    owner_guard(authorization)
    return audit_log[-200:]
