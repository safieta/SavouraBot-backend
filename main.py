from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Configurer l'API Google
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set!")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# Cache simple pour éviter trop d'appels API
cache = {}
cache_ttl = timedelta(hours=1)

# Réponses pré-générées pour fonctionner sans quota
responses_fallback = {
    "recette": "Voici une délicieuse recette de poulet yassa sénégalais : Faites mariner le poulet dans du jus de citron, des oignons tranchés et de l'huile d'arachide pendant 2h. Faites dorer le poulet, puis ajoutez la marinade et laissez mijoter 45 minutes. Servez avec du riz blanc. 🍛",
    "bonjour": "Bonjour ! Je suis SavouraBot, votre assistant pour les recettes africaines. Comment puis-je vous aider ? Vous pouvez me demander une recette, des conseils culinaires ou en savoir plus sur les ingrédients africains. 🍛",
    "jollof": "Le Jollof Rice est un plat populaire en Afrique de l'Ouest. Faites revenir les oignons, ajoutez la tomate, le bouillon, le riz, et les épices. Laissez cuire 30 minutes à feu moyen. C'est délicieux ! 🍛",
}

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
    return {"message": "SavouraBot Backend is running! 🍛", "status": "ok"}

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        # Vérifier le cache
        if req.message in cache:
            cached_reply, cached_time = cache[req.message]
            if datetime.now() - cached_time < cache_ttl:
                return {"reply": cached_reply}
        
        # Utiliser Google Generative AI pour générer une réponse intelligente
        response = model.generate_content(
            f"Tu es SavouraBot, un assistant culinaire spécialisé dans les recettes africaines. "
            f"Réponds en français à la question suivante de manière utile et engageante:\n\n{req.message}"
        )
        reply = response.text
        
        # Mettre en cache
        cache[req.message] = (reply, datetime.now())
        
    except Exception as e:
        error_msg = str(e)
        # Si quota dépassé, utiliser les réponses fallback
        if "429" in error_msg or "quota" in error_msg.lower():
            # Chercher une réponse correspondante
            reply = None
            message_lower = req.message.lower()
            for keyword, fallback_reply in responses_fallback.items():
                if keyword in message_lower:
                    reply = fallback_reply
                    break
            
            if not reply:
                reply = "🍛 Je suis temporairement limité par mon quota API. Essayez de demander une recette de poulet, jollof, ou saluez-moi ! Ou réessayez dans quelques minutes."
        elif "404" in error_msg:
            reply = "🍛 Le modèle n'est pas disponible. Veuillez vérifier votre clé API."
        else:
            reply = f"🍛 Désolé, une erreur s'est produite : {error_msg[:100]}"

    return {
        "reply": reply
    }
