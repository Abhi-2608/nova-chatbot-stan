from typing import List, Dict, Optional, Literal
from datetime import datetime
import json

class ShortTermMemory:
    """
    Manages conversation history with automatic truncation and token awareness.
    """
    
    def __init__(
        self, 
        max_turns: int = 12, 
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None
    ):
        """
        Initialize short-term memory.
        
        Args:
            max_turns: Maximum number of conversation turns to keep (user + assistant = 2 turns)
            max_tokens: Optional token limit (approximate, based on character count)
            system_message: Optional system message to prepend to conversation
        """
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.system_message = system_message
        self.messages: List[Dict[str, str]] = []
        self._metadata: List[Dict] = []  # Store timestamps and other metadata
    
    def add(
        self, 
        role: Literal["user", "assistant", "system"], 
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Message role (user, assistant, or system)
            content: Message content
            metadata: Optional metadata (timestamp, token count, etc.)
        """
        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")
        
        if role not in ["user", "assistant", "system"]:
            raise ValueError(f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'")
        
        message = {"role": role, "content": content.strip()}
        self.messages.append(message)
        
        # Store metadata separately
        meta = metadata or {}
        meta["timestamp"] = datetime.now().isoformat()
        meta["char_count"] = len(content)
        self._metadata.append(meta)
        
        # Trim to max turns (keep system messages)
        self._trim_messages()
    
    def _trim_messages(self) -> None:
        """Trim messages to respect max_turns and max_tokens constraints."""
        # Separate system messages from conversation
        system_msgs = [msg for msg in self.messages if msg["role"] == "system"]
        conversation_msgs = [msg for msg in self.messages if msg["role"] != "system"]
        
        # Keep only last max_turns messages
        if len(conversation_msgs) > self.max_turns:
            removed_count = len(conversation_msgs) - self.max_turns
            conversation_msgs = conversation_msgs[-self.max_turns:]
            self._metadata = self._metadata[removed_count:]
        
        # Combine back
        self.messages = system_msgs + conversation_msgs
        
        # Trim by tokens if needed (approximate: 1 token ≈ 4 characters)
        if self.max_tokens:
            self._trim_by_tokens()
    
    def _trim_by_tokens(self) -> None:
        """Trim messages to fit within token limit (approximate)."""
        estimated_tokens = sum(len(msg["content"]) // 4 for msg in self.messages)
        
        # Remove oldest non-system messages until under limit
        while estimated_tokens > self.max_tokens and len(self.messages) > 1:
            # Find first non-system message
            for i, msg in enumerate(self.messages):
                if msg["role"] != "system":
                    removed_msg = self.messages.pop(i)
                    if i < len(self._metadata):
                        self._metadata.pop(i)
                    estimated_tokens -= len(removed_msg["content"]) // 4
                    break
    
    def get(self, include_system: bool = True) -> List[Dict[str, str]]:
        """
        Get all messages in the conversation history.
        
        Args:
            include_system: Whether to include system messages
            
        Returns:
            List of message dictionaries
        """
        if include_system:
            return self.messages.copy()
        return [msg for msg in self.messages if msg["role"] != "system"]
    
    def get_formatted(self, include_system: bool = True) -> str:
        """
        Get conversation history as formatted string.
        
        Args:
            include_system: Whether to include system messages
            
        Returns:
            Formatted conversation string
        """
        messages = self.get(include_system)
        formatted = []
        
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            formatted.append(f"{role}: {content}")
        
        return "\n\n".join(formatted)
    
    def get_last_n(self, n: int, include_system: bool = False) -> List[Dict[str, str]]:
        """
        Get last N messages.
        
        Args:
            n: Number of messages to retrieve
            include_system: Whether to include system messages
            
        Returns:
            List of last N messages
        """
        messages = self.get(include_system)
        return messages[-n:] if n > 0 else []
    
    def get_context_summary(self) -> Dict:
        """
        Get summary statistics about the conversation.
        
        Returns:
            Dictionary with conversation statistics
        """
        return {
            "total_messages": len(self.messages),
            "user_messages": sum(1 for msg in self.messages if msg["role"] == "user"),
            "assistant_messages": sum(1 for msg in self.messages if msg["role"] == "assistant"),
            "system_messages": sum(1 for msg in self.messages if msg["role"] == "system"),
            "estimated_tokens": sum(len(msg["content"]) // 4 for msg in self.messages),
            "total_characters": sum(len(msg["content"]) for msg in self.messages),
            "oldest_message": self._metadata[0]["timestamp"] if self._metadata else None,
            "newest_message": self._metadata[-1]["timestamp"] if self._metadata else None
        }
    
    def clear(self, keep_system: bool = False) -> None:
        """
        Clear all messages from memory.
        
        Args:
            keep_system: If True, keep system messages
        """
        if keep_system:
            system_msgs = [msg for msg in self.messages if msg["role"] == "system"]
            self.messages = system_msgs
            self._metadata = self._metadata[:len(system_msgs)]
        else:
            self.messages = []
            self._metadata = []
    
    def export_to_json(self, filepath: str) -> None:
        """
        Export conversation history to JSON file.
        
        Args:
            filepath: Path to save JSON file
        """
        data = {
            "messages": self.messages,
            "metadata": self._metadata,
            "config": {
                "max_turns": self.max_turns,
                "max_tokens": self.max_tokens
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def import_from_json(self, filepath: str) -> None:
        """
        Import conversation history from JSON file.
        
        Args:
            filepath: Path to JSON file
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.messages = data.get("messages", [])
        self._metadata = data.get("metadata", [])
        
        # Optionally update config
        config = data.get("config", {})
        if "max_turns" in config:
            self.max_turns = config["max_turns"]
        if "max_tokens" in config:
            self.max_tokens = config["max_tokens"]
    
    def set_system_message(self, content: str) -> None:
        """
        Set or update the system message.
        
        Args:
            content: System message content
        """
        # Remove existing system messages
        self.messages = [msg for msg in self.messages if msg["role"] != "system"]
        
        # Add new system message at the beginning
        self.messages.insert(0, {"role": "system", "content": content})
        self._metadata.insert(0, {
            "timestamp": datetime.now().isoformat(),
            "char_count": len(content)
        })
    
    def __len__(self) -> int:
        """Return number of messages in memory."""
        return len(self.messages)
    
    def __repr__(self) -> str:
        """String representation of memory state."""
        return f"ShortTermMemory(messages={len(self.messages)}, max_turns={self.max_turns})"