from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Charger les variables d’environnement
load_dotenv()

# =======================
# CONFIG GEMINI API
# =======================
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# =======================
# CACHE SIMPLE
# =======================
cache = {}
cache_ttl = timedelta(hours=1)

# =======================
# FALLBACK RECIPES (OFFLINE)
# =======================
responses_fallback = {
    "bonjour": "Bonjour ! 👋 Je suis SavouraBot, votre assistant de recettes africaines 🍛",
    "recette": "🍛 Essayez le riz sauce tomate : oignon + tomate + huile + sel, laissez mijoter et servez avec du riz.",
    "jollof": "Le Jollof Rice : oignons, tomate, riz, épices, laissez cuire à feu moyen 30 min.",
    "haricot": "Haricots africains : faites cuire avec oignon, ail, tomate, sel et un peu d’huile.",
    "riz": "Riz simple : rincez le riz, ajoutez 2 volumes d’eau salée, cuire jusqu’à absorption.",
    "poulet": "Poulet en sauce : faites revenir le poulet, ajoutez tomate, oignon, ail et laissez mijoter.",
}

# =======================
# FASTAPI APP
# =======================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://african-recipe-ai.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "SavouraBot Backend is running 🍛"}

# =======================
# REQUEST MODEL
# =======================
class ChatRequest(BaseModel):
    message: str

# =======================
# CHAT ENDPOINT
# =======================
@app.post("/api/chat")
def chat(req: ChatRequest):
    normalized_message = req.message.strip().lower()

    # 1️⃣ Vérifier le cache
    if normalized_message in cache:
        cached_reply, cached_time = cache[normalized_message]
        if datetime.now() - cached_time < cache_ttl:
            return {"reply": cached_reply}

    # 2️⃣ Essayer Gemini
    try:
        response = model.generate_content(
            f"Tu es SavouraBot, un assistant culinaire spécialisé dans les recettes africaines. "
            f"Réponds en français de façon claire et pratique.\n\nQuestion : {req.message}"
        )
        reply = response.text
        cache[normalized_message] = (reply, datetime.now())
        return {"reply": reply}

    # 3️⃣ Si quota dépassé → fallback intelligent
    except Exception:
        for keyword, fallback_reply in responses_fallback.items():
            if keyword in normalized_message:
                return {"reply": fallback_reply}

        # fallback générique
        return {
            "reply": (
                "🍛 Voici une recette simple :\n\n"
                "👉 Riz aux haricots africain\n"
                "- Haricots + oignon + tomate\n"
                "- Un peu d’huile et de sel\n"
                "- Servir avec du riz chaud\n\n"
                "Astuce : ajoutez du piment ou du poisson fumé 😉"
            )
        }
