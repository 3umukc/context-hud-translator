import json
import httpx
from typing import AsyncGenerator, Dict
from services.translator_base import BaseTranslator

class GroqTranslator(BaseTranslator):
    """
    Groq Cloud API Provider (Ultra-low latency LLM inference with streaming).
    Uses Llama-3.3-70b-versatile or Llama-3.1-8b-instant.
    """
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str = "", model: str = DEFAULT_MODEL):
        super().__init__("Groq Cloud (Llama 3.3)")
        self.api_key = api_key.strip()
        self.model = model

    def set_api_key(self, key: str):
        self.api_key = key.strip()

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def translate_stream(
        self,
        text: str,
        prompts: Dict[str, str],
        target_lang: str = "ru"
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield "[Groq: API ключ не задан. Перейдите в Настройки]"
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = [
            {"role": "system", "content": prompts.get("system_instruction", "")},
            {"role": "user", "content": prompts.get("user_prompt", text)}
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "stream": True,
            "max_tokens": 1024
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                async with client.stream("POST", self.API_URL, json=payload, headers=headers) as response:
                    if response.status_code == 429:
                        yield "[Groq: Превышен рейт-лимит (429 Rate Limit)]"
                        return
                    if response.status_code == 401 or response.status_code == 403:
                        yield f"[Groq: Ошибка авторизации ({response.status_code}). Проверьте API ключ]"
                        return
                    if response.status_code != 200:
                        yield f"[Groq: Ошибка сервера ({response.status_code})]"
                        return

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        json_str = line[len("data: "):].strip()
                        if json_str == "[DONE]":
                            break
                        try:
                            data = json.loads(json_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                chunk_text = delta.get("content", "")
                                if chunk_text:
                                    yield chunk_text
                        except Exception:
                            continue
            except httpx.RequestError as e:
                yield f"[Groq: Сетевая ошибка: {str(e)}]"
