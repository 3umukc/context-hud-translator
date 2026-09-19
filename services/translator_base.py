from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Optional

class BaseTranslator(ABC):
    """
    Abstract Base Class for translation providers.
    Supports both streaming output and one-shot translation.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider has necessary keys/dependencies configured."""
        pass

    @abstractmethod
    async def translate_stream(
        self,
        text: str,
        prompts: Dict[str, str],
        target_lang: str = "ru"
    ) -> AsyncGenerator[str, None]:
        """
        Yields translated text chunks as they arrive.
        prompts contains 'system_instruction' and 'user_prompt'.
        """
        yield ""

    async def translate(
        self,
        text: str,
        prompts: Dict[str, str],
        target_lang: str = "ru"
    ) -> str:
        """Default one-shot translation by collecting streaming tokens."""
        collected = []
        async for chunk in self.translate_stream(text, prompts, target_lang):
            collected.append(chunk)
        return "".join(collected).strip()
