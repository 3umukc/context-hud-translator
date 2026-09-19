import re
import json
import socket
import httpx
from typing import AsyncGenerator, Dict
from services.translator_base import BaseTranslator
from core.dictionary import translate_phrase_or_tokens

class OfflineTranslator(BaseTranslator):
    """
    Offline Fallback Translation Engine.
    1. Fast non-blocking check if local Ollama (localhost:11434) is responsive.
    2. Instant high-performance local dictionary and phrase engine with WSD support.
    """

    def __init__(self):
        super().__init__("Offline Engine")

    def is_available(self) -> bool:
        return True

    def _is_ollama_alive(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", 11434), timeout=0.12):
                return True
        except (OSError, ConnectionRefusedError):
            return False

    async def _try_ollama_stream(self, text: str, prompts: Dict[str, str]) -> AsyncGenerator[str, None]:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "qwen2.5:3b",
            "prompt": f"{prompts.get('system_instruction', '')}\n\n{prompts.get('user_prompt', text)}",
            "stream": True
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            yield data.get("response", "")

    async def translate_stream(
        self,
        text: str,
        prompts: Dict[str, str],
        target_lang: str = "ru"
    ) -> AsyncGenerator[str, None]:
        # 1. Quick check for Ollama before attempting stream
        if self._is_ollama_alive():
            try:
                has_tokens = False
                async for token in self._try_ollama_stream(text, prompts):
                    has_tokens = True
                    yield token
                if has_tokens:
                    return
            except Exception:
                pass

        # 2. Extract any WSD session anchors from system instruction
        system_instruction = prompts.get("system_instruction", "")
        anchors_dict: Dict[str, str] = {}
        matches = re.findall(r"'([\w-]+)' MUST be translated according to domain \[.+?\] as '(.+?)'", system_instruction)
        for term, trans in matches:
            anchors_dict[term.lower()] = trans

        # 3. Translate using comprehensive offline dictionary and phrase engine
        result = translate_phrase_or_tokens(text, custom_anchors=anchors_dict)
        yield result
