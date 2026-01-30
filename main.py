from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional

load_dotenv()

# =============================
# CONFIGURATION GEMINI
# =============================
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set!")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

# =============================
# SYSTEM PROMPT (TON ASSISTANT)
# =============================
SYSTEM_PROMPT = """
Tu es un assistant culinaire expert spécialisé dans les recettes africaines,
en particulier celles d’Afrique de l’Ouest.

Tu génères des recettes complètes, authentiques et faciles à suivre,
avec un ton chaleureux et engageant.

FORMAT OBLIGATOIRE :

🍲 NOM DU PLAT
🥘 INGRÉDIENTS (avec quantités)
👩🏽‍🍳 ÉTAPES DE PRÉPARATION (numérotées)
💡 CONSEILS SUPPLÉMENTAIRES

RÈGLES :
- Réponds uniquement en français
- Utilise des emojis culinaires avec modération 🍛🥘
- N’invente jamais d’informations
- Si un détail manque, dis-le clairement
- Ne sors jamais du format imposé
"""

# =============================
# CACHE SIMPLE
# =============================
cache = {}
cache_ttl = timedelta(hours=1)

# =============================
# FASTAPI APP
# =============================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "SavouraBot Backend is running 🍛",
        "status": "ok"
    }

# =============================
# SCHEMA REQUÊTE
# =============================
class ChatRequest(BaseModel):
    message: Optional[str] = None
    prompt: Optional[str] = None

# =============================
# ENDPOINT CHAT
# =============================
@app.post("/api/chat")
def chat(req: ChatRequest):
    user_message = req.message or req.prompt

    if not user_message:
        return {
            "reply": "🍛 Veuillez fournir un message ou un prompt."
        }

    # Cache
    if user_message in cache:
        cached_reply, cached_time = cache[user_message]
        if datetime.now() - cached_time < cache_ttl:
            return {"reply": cached_reply}

    try:
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nQUESTION UTILISATEUR : {user_message}"
        )

        reply = response.text.strip()

        cache[user_message] = (reply, datetime.now())

        return {"reply": reply}

    except Exception as e:
        error = str(e).lower()

        # Gestion réaliste des erreurs
        if "quota" in error or "429" in error:
            reply = (
                "🍛 Le service est temporairement indisponible (quota atteint). "
                "Réessayez dans quelques minutes."
            )
        elif "api key" in error or "permission" in error:
            reply = (
                "🍛 Problème avec la clé API Gemini. "
                "Vérifiez qu’elle est valide et bien liée à un projet."
            )
        else:
            reply = (
                "🍛 Une erreur interne est survenue. "
                "Veuillez réessayer plus tard."
            )

        return {"reply": reply}
