import os
from typing import Dict, List, Optional
from datetime import datetime

from memory.short_term import ShortTermMemory
from memory.long_term import get_user_profile, upsert_user_profile
from memory.vector_store import VectorMemory
from models.gemini_client import GeminiClient


class NovaChatbot:
    

    def __init__(self, api_key: Optional[str] = None):
        # Load API key
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found.")

        # Initialize Gemini client (MODULAR & CLEAN)
        self.llm = GeminiClient(api_key=self.api_key)

        # Load system prompt
        self.system_prompt = self._load_system_prompt()

        # Memory systems
        self.vector_memory = VectorMemory()
        self.sessions: Dict[str, ShortTermMemory] = {}

    def _load_system_prompt(self) -> str:
        try:
            with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "You are Nova, a thoughtful and empathetic conversational companion."

    def _get_session(self, user_id: str) -> ShortTermMemory:
        if user_id not in self.sessions:
            self.sessions[user_id] = ShortTermMemory(max_turns=12)
        return self.sessions[user_id]

    def _build_context(self, user_id: str, message: str) -> str:
        context = []

        # 1. System identity + rules
        context.append(self.system_prompt)
        context.append("\nInstruction: Match the user's emotional tone naturally.")
        context.append("\n" + "=" * 50)

        # 2. Long-term memory (facts only)
        profile = get_user_profile(user_id)
        if profile:
            context.append("USER PROFILE:")
            for k, v in profile.items():
                if v:
                    if isinstance(v, list):
                        context.append(f"- {k}: {', '.join(v)}")
                    else:
                        context.append(f"- {k}: {v}")
            context.append("")

        # 3. Vector memory (safe summaries only)
        memories = self.vector_memory.retrieve_memories(user_id, message, k=3)
        if memories:
            context.append("RELEVANT PAST CONTEXT:")
            for mem in memories:
                context.append(f"- {mem['text']}")
            context.append("")

        # 4. Short-term memory
        session = self._get_session(user_id)
        history = session.get(include_system=False)
        if history:
            context.append("CURRENT CONVERSATION:")
            for msg in history[-6:]:
                role = msg["role"].capitalize()
                context.append(f"{role}: {msg['content']}")
            context.append("")

        context.append("=" * 50)
        context.append(f"User: {message}")
        context.append("Nova:")

        return "\n".join(context)

    def _extract_profile_updates(self, message: str) -> Dict:
        updates = {}
        msg = message.lower()

        # Name (explicit only)
        if "my name is" in msg:
            name = message.split("my name is")[-1].strip().split()[0].strip(".,!?")
            updates["name"] = name

        # Location (explicit only)
        if "i live in" in msg:
            location = message.split("i live in")[-1].strip().split(".")[0]
            updates["location"] = location

        return updates

    async def chat(self, user_id: str, message: str) -> Dict:
        if not message.strip():
            return {"response": "Could you say that again?"}

        session = self._get_session(user_id)
        session.add("user", message)

        context = self._build_context(user_id, message)

        # 🔹 LLM CALL VIA GeminiClient (IMPORTANT CHANGE)
        response_text = self.llm.generate(context)

        session.add("assistant", response_text)

        # Store safe summary in vector memory
        summary = f"User discussed: {message[:120]}"
        self.vector_memory.store_memory(user_id, summary)

        # Update profile safely
        updates = self._extract_profile_updates(message)
        existing_profile = get_user_profile(user_id)

        for field, value in updates.items():
            existing = existing_profile.get(field)
            if existing and existing != value:
                return {
                    "response": f"I remember you said {existing} earlier. Want me to update it to {value}?"
                }
            upsert_user_profile(user_id, field, value)

        return {
            "response": response_text,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "profile_updated": bool(updates)
        }

    def chat_sync(self, user_id: str, message: str) -> Dict:
        import asyncio
        return asyncio.run(self.chat(user_id, message))

    def clear_session(self, user_id: str):
        if user_id in self.sessions:
            self.sessions[user_id].clear()

    def get_conversation_history(self, user_id: str) -> List[Dict]:
        if user_id in self.sessions:
            return self.sessions[user_id].get()
        return []
