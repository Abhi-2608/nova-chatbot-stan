import os
import google.generativeai as genai
from typing import Optional
import time


class GeminiClient:
    """
    Thin wrapper around Google Gemini 2.5 Flash.
    Keeps all LLM configuration and calls in one place.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google Gemini API key (or set GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set it as environment variable or pass directly.")
        
        genai.configure(api_key=self.api_key)
        
        # Gemini 2.5 Flash (as required by STAN)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.85,      # Natural but controlled
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 800  # Cost-aware
            }
        )
        
        # Track API usage for debugging/monitoring
        self.call_count = 0
        self.total_tokens_estimate = 0
    
    def generate(self, prompt: str, retry_count: int = 2) -> str:
        """
        Generate a response from Gemini with retry logic.
        
        Args:
            prompt: The prompt to send to Gemini
            retry_count: Number of retries on failure
            
        Returns:
            Generated response text
        """
        if not prompt or not prompt.strip():
            return "I didn't receive a clear message. Could you try again?"
        
        for attempt in range(retry_count + 1):
            try:
                response = self.model.generate_content(prompt)
                
                # Update usage tracking
                self.call_count += 1
                # Rough estimate: 4 chars ≈ 1 token
                self.total_tokens_estimate += (len(prompt) + len(response.text)) // 4
                
                return response.text.strip()
                
            except Exception as e:
                print(f"Gemini API error (attempt {attempt + 1}/{retry_count + 1}): {e}")
                
                # If rate limited, wait before retry
                if "quota" in str(e).lower() or "rate" in str(e).lower():
                    if attempt < retry_count:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        print(f"Rate limited. Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                
                # If not last attempt, retry
                if attempt < retry_count:
                    time.sleep(1)
                    continue
                
                # Last attempt failed - return safe fallback
                return "I'm having a bit of trouble responding right now. Could you try again?"
        
        # Should never reach here, but just in case
        return "I'm having trouble connecting right now."
    
    async def generate_async(self, prompt: str, retry_count: int = 2) -> str:
        """
        Async version of generate (for FastAPI async endpoints).
        
        Args:
            prompt: The prompt to send to Gemini
            retry_count: Number of retries on failure
            
        Returns:
            Generated response text
        """
        # Note: google-generativeai doesn't have native async support yet
        # So we'll use the sync version - FastAPI will handle it in a thread pool
        return self.generate(prompt, retry_count)
    
    def get_stats(self) -> dict:
        """
        Get usage statistics.
        
        Returns:
            Dictionary with call count and token estimates
        """
        return {
            "total_calls": self.call_count,
            "estimated_tokens": self.total_tokens_estimate,
            "estimated_cost": self.total_tokens_estimate * 0.00001  # Rough estimate
        }
    
    def reset_stats(self):
        """Reset usage statistics."""
        self.call_count = 0
        self.total_tokens_estimate = 0


# Convenience function for simple usage
_global_client = None

def get_client(api_key: Optional[str] = None) -> GeminiClient:
    """Get or create global Gemini client instance."""
    global _global_client
    if _global_client is None:
        _global_client = GeminiClient(api_key)
    return _global_client


def generate_response(prompt: str) -> str:
    """
    Simple function to generate response using global client.
    Useful for backward compatibility.
    """
    client = get_client()
    return client.generate(prompt)