import httpx
from typing import Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from bot.config import settings
from .base import BaseLLMClient

class GroqClient(BaseLLMClient):
    """Client for Groq API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key 
        self.base_url = "https://api.groq.com/openai/v1"
        self.last_prompt_tokens = 0
        self.last_completion_tokens = 0
        self.last_total_tokens = 0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_text(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.7, 
        max_tokens: Optional[int] = None
    ) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set.")
            
        logger.info(f"Using Groq Key starting with: '{self.api_key[:5]}...' (Length: {len(self.api_key)})")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.3-70b-versatile",  # Official Groq model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", 
                    headers=headers, 
                    json=payload
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(f"Groq API Error body: {e.response.text}")
                    raise
                data = response.json()
                usage = data.get("usage", {})
                self.last_prompt_tokens = usage.get("prompt_tokens", 0)
                self.last_completion_tokens = usage.get("completion_tokens", 0)
                self.last_total_tokens = usage.get("total_tokens", 0)
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise
