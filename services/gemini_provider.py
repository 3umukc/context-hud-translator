import json
import httpx
from typing import AsyncGenerator, Dict
from services.translator_base import BaseTranslator

class GeminiTranslator(BaseTranslator):
    """
    Google Gemini Free Tier Translation Provider with Server-Sent Events (SSE) streaming.
    """
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str = "", model: str = DEFAULT_MODEL):
        super().__init__("Google Gemini")
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
            yield "[Gemini: API ключ не задан. Перейдите в Настройки]"
            return

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompts.get("user_prompt", text)}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": prompts.get("system_instruction", "")}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                async with client.stream("POST", url, json=payload, headers={"Content-Type": "application/json"}) as response:
                    if response.status_code == 429:
                        yield "[Gemini: Превышен лимит запросов (429 Quota Exceeded)]"
                        return
                    if response.status_code == 400 or response.status_code == 403:
                        yield f"[Gemini: Ошибка авторизации ({response.status_code}). Проверьте API ключ]"
                        return
                    if response.status_code != 200:
                        yield f"[Gemini: Ошибка сервера ({response.status_code})]"
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
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    chunk_text = part.get("text", "")
                                    if chunk_text:
                                        yield chunk_text
                        except Exception:
                            continue
            except httpx.RequestError as e:
                yield f"[Gemini: Сетевая ошибка: {str(e)}]"
