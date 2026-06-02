import httpx
import uuid
from typing import Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from bot.config import settings
from .base import BaseLLMClient

class GigaChatClient(BaseLLMClient):
    """Client for Sber GigaChat API."""

    def __init__(self, auth_key: Optional[str] = None):
        self.auth_key = auth_key or settings.gigachat_auth_key
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.access_token = None
        self.last_prompt_tokens = 0
        self.last_completion_tokens = 0
        self.last_total_tokens = 0

    async def _authenticate(self) -> None:
        """Fetch a new access token from GigaChat OAuth."""
        if not self.auth_key:
            raise ValueError("GIGACHAT_AUTH_KEY is not set.")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {self.auth_key}"
        }
        data = {"scope": "GIGACHAT_API_PERS"}

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(self.auth_url, headers=headers, data=data)
            response.raise_for_status()
            self.access_token = response.json().get("access_token")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_text(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.7, 
        max_tokens: Optional[int] = None
    ) -> str:
        if not self.access_token:
            await self._authenticate()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

        payload = {
            "model": "GigaChat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", 
                    headers=headers, 
                    json=payload
                )
                
                # If token expired, auth error -> re-auth and raise to retry
                if response.status_code == 401:
                    logger.warning("GigaChat token expired, re-authenticating...")
                    self.access_token = None
                    await self._authenticate()
                    response.raise_for_status() # Trigger retry

                response.raise_for_status()
                data = response.json()
                usage = data.get("usage", {})
                self.last_prompt_tokens = usage.get("prompt_tokens", 0)
                self.last_completion_tokens = usage.get("completion_tokens", 0)
                self.last_total_tokens = usage.get("total_tokens", 0)
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling GigaChat API: {e}")
            raise
