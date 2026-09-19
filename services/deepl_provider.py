import httpx
from typing import AsyncGenerator, Dict
from services.translator_base import BaseTranslator

class DeepLTranslator(BaseTranslator):
    """
    DeepL Free API Provider.
    Supports native 'context' parameter for word-sense disambiguation.
    """
    FREE_API_URL = "https://api-free.deepl.com/v2/translate"

    def __init__(self, api_key: str = ""):
        super().__init__("DeepL Free API")
        self.api_key = api_key.strip()

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
            yield "[DeepL: API ключ не задан. Перейдите в Настройки]"
            return

        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/json"
        }

        # Map language codes
        lang_target = target_lang.upper()
        if lang_target == "EN":
            lang_target = "EN-US"

        payload = {
            "text": [text],
            "target_lang": lang_target
        }

        # If surrounding context exists, pass it to DeepL's context parameter
        system_instruction = prompts.get("system_instruction", "")
        user_prompt = prompts.get("user_prompt", "")
        # Extract surrounding context if present
        if "<SURROUNDING_CONTEXT>" in user_prompt:
            try:
                ctx_start = user_prompt.find("<SURROUNDING_CONTEXT>") + len("<SURROUNDING_CONTEXT>")
                ctx_end = user_prompt.find("</SURROUNDING_CONTEXT>")
                context_str = user_prompt[ctx_start:ctx_end].strip()
                if context_str:
                    payload["context"] = context_str
            except Exception:
                pass

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.FREE_API_URL, json=payload, headers=headers)
                if response.status_code == 429:
                    yield "[DeepL: Превышена квота или лимит запросов (429)]"
                    return
                if response.status_code == 403:
                    yield "[DeepL: Неверный ключ авторизации (403)]"
                    return
                if response.status_code != 200:
                    yield f"[DeepL: Ошибка сервера ({response.status_code})]"
                    return

                data = response.json()
                translations = data.get("translations", [])
                if translations:
                    result = translations[0].get("text", "")
                    yield result
            except httpx.RequestError as e:
                yield f"[DeepL: Ошибка соединения: {str(e)}]"
