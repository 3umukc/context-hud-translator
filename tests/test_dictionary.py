import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from core.dictionary import translate_phrase_or_tokens

class TestDictionaryEngine(unittest.TestCase):
    def test_phrase_translation(self):
        self.assertEqual(translate_phrase_or_tokens("how are you"), "как дела")
        self.assertEqual(translate_phrase_or_tokens("good morning"), "доброе утро")
        self.assertEqual(translate_phrase_or_tokens("thank you very much"), "большое спасибо")

    def test_single_word_translation(self):
        self.assertEqual(translate_phrase_or_tokens("hello"), "привет")
        self.assertEqual(translate_phrase_or_tokens("world"), "мир")
        self.assertEqual(translate_phrase_or_tokens("garden"), "сад")

    def test_wsd_custom_anchor(self):
        # Without anchor, leaf is "лист растения"
        res1 = translate_phrase_or_tokens("green leaf")
        self.assertIn("лист растения", res1)

        # With anchor overridden to sheet of paper
        res2 = translate_phrase_or_tokens("clipped a leaf", custom_anchors={"leaf": "лист бумаги"})
        self.assertIn("лист бумаги", res2)

    def test_morphology_heuristics(self):
        # Test plural
        res = translate_phrase_or_tokens("plants and trees")
        self.assertIn("растения", res)
        self.assertIn("деревья", res)

    def test_ru_to_en_phrases(self):
        self.assertEqual(translate_phrase_or_tokens("как дела"), "how are you")
        self.assertEqual(translate_phrase_or_tokens("добрый день"), "good afternoon")
        self.assertEqual(translate_phrase_or_tokens("спасибо большое"), "thank you very much")

    def test_ru_to_en_inflections_and_case(self):
        self.assertEqual(translate_phrase_or_tokens("привет"), "hello")
        self.assertEqual(translate_phrase_or_tokens("Привет"), "Hello")
        self.assertEqual(translate_phrase_or_tokens("ПРИВЕТ"), "HELLO")
        self.assertEqual(translate_phrase_or_tokens("машину"), "car")
        self.assertEqual(translate_phrase_or_tokens("делаешь"), "are doing")
        self.assertEqual(translate_phrase_or_tokens("книги"), "books")

    def test_multi_language_sl_tl(self):
        # Russian to German
        res_de = translate_phrase_or_tokens("привет", sl="ru", tl="de")
        self.assertIn(res_de.lower(), ["hallo", "tag", "grüß gott", "servus"])

        # English to Spanish
        res_es = translate_phrase_or_tokens("hello", sl="en", tl="es")
        self.assertEqual(res_es.lower(), "hola")

    def test_context_reset_sim(self):
        from windows.hooks import WinHookWorker
        worker = WinHookWorker()
        worker._sentence_words = ["Сколько", "языков"]
        worker._sentence_translated_text = "How many languages "
        worker._typed_chars = ["п", "о", "д"]

        # Simulate Ctrl+A / reset
        worker._reset_sentence_context()

        self.assertEqual(worker._sentence_words, [])
        self.assertEqual(worker._sentence_translated_text, "")
        self.assertEqual(worker._typed_chars, [])

if __name__ == "__main__":
    unittest.main()
