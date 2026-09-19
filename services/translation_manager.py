from typing import AsyncGenerator, Dict, Optional, Tuple
from config import config
from services.translator_base import BaseTranslator
from services.gemini_provider import GeminiTranslator
from services.groq_provider import GroqTranslator
from services.deepl_provider import DeepLTranslator
from services.offline_provider import OfflineTranslator

class TranslationManager:
    """
    Orchestrates translation providers, manages failover, handles caching,
    and returns stream of translated chunks.
    """
    def __init__(self):
        self.gemini = GeminiTranslator()
        self.groq = GroqTranslator()
        self.deepl = DeepLTranslator()
        self.offline = OfflineTranslator()
        self._cache: Dict[str, str] = {}
        self.reload_config()

    def reload_config(self):
        keys = config.get("api_keys", {})
        self.gemini.set_api_key(keys.get("gemini", ""))
        self.groq.set_api_key(keys.get("groq", ""))
        self.deepl.set_api_key(keys.get("deepl", ""))

    def get_preferred_provider(self) -> Tuple[BaseTranslator, str]:
        mode = config.get("provider", "auto").lower()

        if mode == "gemini" and self.gemini.is_available():
            return self.gemini, "Gemini"
        elif mode == "groq" and self.groq.is_available():
            return self.groq, "Groq (Llama 3.3)"
        elif mode == "deepl" and self.deepl.is_available():
            return self.deepl, "DeepL"
        elif mode == "offline":
            return self.offline, "Offline Fallback"

        # Auto Mode Priority: Groq -> Gemini -> DeepL -> Offline
        if self.groq.is_available():
            return self.groq, "Groq"
        if self.gemini.is_available():
            return self.gemini, "Gemini"
        if self.deepl.is_available():
            return self.deepl, "DeepL"

        return self.offline, "Offline Fallback"

    async def translate_stream(
        self,
        text: str,
        prompts: Dict[str, str],
        target_lang: str = "ru"
    ) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Yields (chunk_text, provider_name).
        Handles automatic failover if chosen cloud API fails.
        """
        provider, provider_name = self.get_preferred_provider()
        
        # Stream from primary provider
        stream_chunks = []
        is_error = False

        try:
            async for chunk in provider.translate_stream(text, prompts, target_lang):
                # Check for explicit provider error messages in output
                if chunk.startswith("[") and ("Ошибка" in chunk or "Превышен" in chunk or "не задан" in chunk):
                    is_error = True
                    break
                stream_chunks.append(chunk)
                yield chunk, provider_name
        except Exception as e:
            is_error = True

        # If primary failed and it wasn't already offline, failover to offline
        if is_error and provider != self.offline:
            fallback_name = "Offline Fallback (Auto-switch)"
            yield "\n[Переключение на резервный офлайн-движок]\n", fallback_name
            async for chunk in self.offline.translate_stream(text, prompts, target_lang):
                yield chunk, fallback_name
