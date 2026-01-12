from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from contextlib import asynccontextmanager

from backened.chatbot import NovaChatbot
from memory.long_term import get_user_profile, upsert_user_profile, init_db
from memory.vector_store import VectorMemory


# -----------------------------
# Global instances
# -----------------------------
chatbot: Optional[NovaChatbot] = None
vector_memory = VectorMemory()


# -----------------------------
# App lifecycle (CORRECT PLACE)
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global chatbot

    print("Initializing database...")
    init_db()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    print("Initializing NovaChatbot...")
    chatbot = NovaChatbot(api_key=api_key)
    print("NovaChatbot initialized successfully")

    yield

    print("Shutting down application...")


app = FastAPI(
    title="Nova Chatbot API",
    description="Human-like conversational AI with long-term memory",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev only
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Request models
# -----------------------------
class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    user_id: str
    timestamp: str
    profile_updated: bool = False


class ProfileUpdate(BaseModel):
    field: str
    value: str


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def root():
    return {"status": "online", "bot": "Nova"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not chatbot:
        raise HTTPException(503, "Chatbot not initialized")

    result = await chatbot.chat(
        user_id=request.user_id,
        message=request.message
    )
    return ChatResponse(**result)


@app.get("/profile/{user_id}")
def get_profile(user_id: str):
    return {
        "user_id": user_id,
        "profile": get_user_profile(user_id)
    }


@app.post("/profile/{user_id}")
def update_profile(user_id: str, update: ProfileUpdate):
    profile = get_user_profile(user_id)
    existing = profile.get(update.field)

    if existing and existing != update.value:
        raise HTTPException(
            status_code=409,
            detail=f"Existing value is '{existing}'. Confirm change explicitly."
        )

    upsert_user_profile(user_id, update.field, update.value)
    return {"status": "updated"}


@app.get("/history/{user_id}")
def get_history(user_id: str):
    if not chatbot:
        raise HTTPException(503, "Chatbot not initialized")

    history = chatbot.get_conversation_history(user_id)
    return {
        "user_id": user_id,
        "messages": history
    }


@app.post("/clear-session/{user_id}")
def clear_session(user_id: str):
    chatbot.clear_session(user_id)
    return {"status": "cleared"}


@app.get("/memories/{user_id}")
def get_memories(user_id: str, limit: int = 5):
    memories = vector_memory.get_user_memories(user_id, limit=limit)
    return {
        "user_id": user_id,
        "memories": [
            {"text": m["text"], "timestamp": m["timestamp"]}
            for m in memories
        ]
    }
