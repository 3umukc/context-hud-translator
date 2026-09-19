import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from services.translation_manager import TranslationManager
from services.offline_provider import OfflineTranslator

class TestTranslationProviders(unittest.TestCase):
    def setUp(self):
        self.mgr = TranslationManager()
        self.offline = OfflineTranslator()

    def test_offline_translator_availability(self):
        self.assertTrue(self.offline.is_available())

    def test_offline_wsd_translation(self):
        prompts = {
            "system_instruction": "Strict Terminology & Word-Sense Disambiguation Anchors:\n- 'leaf' MUST be translated according to domain [botany] as 'лист растения'",
            "user_prompt": "green leaf"
        }
        
        async def run_test():
            chunks = []
            async for chunk in self.offline.translate_stream("green leaf", prompts, "ru"):
                chunks.append(chunk)
            return "".join(chunks)

        result = asyncio.run(run_test())
        self.assertIn("лист растения", result)

    def test_translation_manager_fallback(self):
        # Without API keys, preferred provider should default to offline or correctly identify fallback
        provider, name = self.mgr.get_preferred_provider()
        self.assertIsNotNone(provider)

if __name__ == "__main__":
    unittest.main()
