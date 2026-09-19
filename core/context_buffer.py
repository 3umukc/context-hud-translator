import re
from typing import Dict, List, Optional, Tuple

class TermAnchors:
    """
    Tracks and enforces consistent semantic meanings for ambiguous terms (homonyms)
    within a translation session to prevent semantic drift (Word-Sense Disambiguation).
    Example: 'leaf' -> 'лист растения (биология)', not 'лист бумаги (канцелярия)'.
    """
    def __init__(self):
        # Maps lowercase source term -> (target meaning/domain, translation)
        # e.g. "leaf": ("plant/botany", "лист растения")
        self.anchors: Dict[str, Dict[str, str]] = {}
        
        # Predefined dictionary of common homonyms and their typical domain options
        self.known_homonyms: Dict[str, List[Dict[str, str]]] = {
            "leaf": [
                {"domain": "botany", "meaning": "plant foliage", "ru": "лист растения"},
                {"domain": "paper", "meaning": "sheet of paper", "ru": "лист бумаги"}
            ],
            "crane": [
                {"domain": "construction", "meaning": "lifting machine", "ru": "подъемный кран"},
                {"domain": "zoology", "meaning": "tall bird", "ru": "журавль"}
            ],
            "bank": [
                {"domain": "finance", "meaning": "financial institution", "ru": "банк (финансовый)"},
                {"domain": "geography", "meaning": "river bank", "ru": "берег реки"}
            ],
            "spring": [
                {"domain": "season", "meaning": "springtime", "ru": "весна"},
                {"domain": "mechanics", "meaning": "coiled metal spring", "ru": "пружина"},
                {"domain": "nature", "meaning": "water spring", "ru": "родник / источник"}
            ],
            "plant": [
                {"domain": "botany", "meaning": "living organism/vegetation", "ru": "растение"},
                {"domain": "industry", "meaning": "factory/facility", "ru": "завод / фабрика"}
            ],
            "bark": [
                {"domain": "botany", "meaning": "tree covering", "ru": "кора дерева"},
                {"domain": "zoology", "meaning": "dog sound", "ru": "собачий лай"}
            ],
            "mouse": [
                {"domain": "tech", "meaning": "computer peripheral", "ru": "компьютерная мышь"},
                {"domain": "zoology", "meaning": "rodent", "ru": "грызун / мышь"}
            ],
            "bow": [
                {"domain": "weapon", "meaning": "archery bow", "ru": "лук (оружие)"},
                {"domain": "gesture", "meaning": "bending forward", "ru": "поклон"}
            ],
            "trunk": [
                {"domain": "botany", "meaning": "tree stem", "ru": "ствол дерева"},
                {"domain": "vehicle", "meaning": "car boot", "ru": "багажник автомобиля"},
                {"domain": "zoology", "meaning": "elephant nose", "ru": "хобот слона"}
            ]
        }

    def set_anchor(self, term: str, domain: str, translation: str):
        term_clean = term.strip().lower()
        self.anchors[term_clean] = {
            "domain": domain,
            "translation": translation
        }

    def remove_anchor(self, term: str):
        term_clean = term.strip().lower()
        if term_clean in self.anchors:
            del self.anchors[term_clean]

    def clear(self):
        self.anchors.clear()

    def get_anchors(self) -> Dict[str, Dict[str, str]]:
        return self.anchors.copy()

    def detect_potential_homonyms(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        detected = []
        for w in words:
            if w in self.known_homonyms and w not in detected:
                detected.append(w)
        return detected

    def format_anchors_prompt(self) -> str:
        if not self.anchors:
            return ""
        lines = ["Strict Terminology & Word-Sense Disambiguation Anchors:"]
        for term, data in self.anchors.items():
            lines.append(f"- '{term}' MUST be translated according to domain [{data['domain']}] as '{data['translation']}'")
        return "\n".join(lines)


class ContextBuffer:
    """
    Maintains a sliding window of recent sentences to preserve semantic context
    for translating sentences, clauses, and phrases without loss of meaning.
    """
    def __init__(self, max_sentences: int = 3):
        self.max_sentences = max_sentences
        self.history_sentences: List[str] = []
        self.term_anchors = TermAnchors()

    def add_sentence(self, sentence: str):
        cleaned = sentence.strip()
        if not cleaned:
            return
        self.history_sentences.append(cleaned)
        if len(self.history_sentences) > self.max_sentences:
            self.history_sentences.pop(0)

    def add_text_chunks(self, text: str):
        # Split text into sentences using regex
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        for s in sentences:
            if s.strip():
                self.add_sentence(s)

    def get_recent_context(self) -> str:
        return " ".join(self.history_sentences)

    def clear(self):
        self.history_sentences.clear()
        self.term_anchors.clear()

    def clear_history_only(self):
        self.history_sentences.clear()
