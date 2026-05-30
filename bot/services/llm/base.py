from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate_text(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.7, 
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text using the LLM.

        Args:
            system_prompt: The system instruction for the LLM.
            user_prompt: The user input for the LLM.
            temperature: The sampling temperature.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            The generated text string.
        """
        pass
