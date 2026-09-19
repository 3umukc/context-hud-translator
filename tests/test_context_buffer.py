import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from core.context_buffer import ContextBuffer, TermAnchors
from core.wsd_engine import WSDEngine

class TestContextAndWSD(unittest.TestCase):
    def setUp(self):
        self.buffer = ContextBuffer(max_sentences=3)
        self.wsd = WSDEngine(self.buffer)

    def test_sliding_window(self):
        self.buffer.add_sentence("First sentence.")
        self.buffer.add_sentence("Second sentence.")
        self.buffer.add_sentence("Third sentence.")
        self.buffer.add_sentence("Fourth sentence.")

        # Should keep only last 3
        recent = self.buffer.get_recent_context()
        self.assertNotIn("First sentence.", recent)
        self.assertIn("Second sentence.", recent)
        self.assertIn("Third sentence.", recent)
        self.assertIn("Fourth sentence.", recent)

    def test_term_anchors_detection(self):
        anchors = self.buffer.term_anchors
        detected = anchors.detect_potential_homonyms("The autumn leaf fell near the river bank.")
        self.assertIn("leaf", detected)
        self.assertIn("bank", detected)

    def test_botany_wsd_inference(self):
        # Provide garden/plant context
        self.buffer.add_sentence("The gardener examined the green plant in the forest.")
        new_text = "He clipped a diseased leaf."
        
        updated = self.wsd.infer_and_update_anchors(new_text)
        active_anchors = self.buffer.term_anchors.get_anchors()

        self.assertIn("leaf", active_anchors)
        self.assertEqual(active_anchors["leaf"]["domain"], "botany")
        self.assertIn("лист растения", active_anchors["leaf"]["translation"])

    def test_prompt_generation_contains_wsd_tags(self):
        self.buffer.term_anchors.set_anchor("leaf", "botany", "лист растения")
        self.buffer.add_sentence("The plant is growing well.")
        
        prompts = self.wsd.build_llm_prompt("Look at that leaf.", target_lang="ru")
        self.assertIn("Strict Terminology & Word-Sense Disambiguation Anchors", prompts["system_instruction"])
        self.assertIn("лист растения", prompts["system_instruction"])
        self.assertIn("<SURROUNDING_CONTEXT>", prompts["user_prompt"])
        self.assertIn("<TRANSLATE_TARGET>", prompts["user_prompt"])

if __name__ == "__main__":
    unittest.main()
