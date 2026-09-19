import re
from typing import Dict, List, Optional, Tuple
from core.context_buffer import ContextBuffer, TermAnchors

class WSDEngine:
    """
    Word-Sense Disambiguation (WSD) Engine.
    Coordinates context buffer, term anchors, and builds specialized
    prompts for translation models to prevent semantic shifts.
    """
    
    # Domain keyword heuristics to automatically infer anchors from context
    DOMAIN_KEYWORDS = {
        "botany": ["plant", "flower", "tree", "garden", "botany", "chlorophyll", "soil", "branch", "stem", "root", "grow", "green", "nature", "forest", "foliage", "herb"],
        "paper": ["paper", "book", "office", "document", "print", "binder", "stationery", "write", "notebook", "desk", "page", "sheet"],
        "finance": ["money", "dollar", "credit", "account", "invest", "deposit", "loan", "economy", "stock", "interest", "teller", "payment"],
        "geography": ["river", "water", "stream", "lake", "shore", "bank", "mud", "flow", "fish", "current", "steep", "sand"],
        "construction": ["machine", "build", "site", "load", "lift", "heavy", "crane", "steel", "concrete", "worker", "contractor"],
        "zoology": ["animal", "bird", "fly", "feather", "nest", "wild", "species", "beast", "fur", "paw", "tail", "rodent", "habitat"],
        "tech": ["computer", "mouse", "keyboard", "screen", "click", "software", "hardware", "cpu", "gpu", "code", "usb", "monitor"]
    }

    def __init__(self, context_buffer: ContextBuffer):
        self.context_buffer = context_buffer

    def infer_and_update_anchors(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Scans both full context and current text to detect ambiguous terms,
        infers their domain based on nearby keywords, and registers them in TermAnchors.
        Returns list of newly discovered or confirmed anchors: (term, domain, ru_translation).
        """
        full_text = (self.context_buffer.get_recent_context() + " " + text).lower()
        detected_terms = self.context_buffer.term_anchors.detect_potential_homonyms(full_text)
        
        updated = []
        for term in detected_terms:
            # Check existing anchor
            existing = self.context_buffer.term_anchors.get_anchors().get(term)
            if existing:
                continue

            # Score each domain for this term
            homonym_options = self.context_buffer.term_anchors.known_homonyms.get(term, [])
            best_domain = None
            max_score = 0
            
            for opt in homonym_options:
                domain = opt["domain"]
                keywords = self.DOMAIN_KEYWORDS.get(domain, [])
                score = sum(1 for kw in keywords if kw in full_text)
                if score > max_score:
                    max_score = score
                    best_domain = opt

            # If strong correlation found or fallback to first default option if context is indicative
            if best_domain and max_score > 0:
                self.context_buffer.term_anchors.set_anchor(
                    term=term,
                    domain=best_domain["domain"],
                    translation=best_domain["ru"]
                )
                updated.append((term, best_domain["domain"], best_domain["ru"]))
            elif homonym_options:
                # Still register as tracked term with first candidate
                first = homonym_options[0]
                self.context_buffer.term_anchors.set_anchor(
                    term=term,
                    domain=first["domain"],
                    translation=first["ru"]
                )
                updated.append((term, first["domain"], first["ru"]))

        return updated

    def build_llm_prompt(self, target_text: str, source_lang: str = "auto", target_lang: str = "ru") -> Dict[str, str]:
        """
        Builds system prompt and user prompt ensuring strict WSD guidelines,
        context window incorporation, and clean output translation.
        """
        context_history = self.context_buffer.get_recent_context()
        anchors_prompt = self.context_buffer.term_anchors.format_anchors_prompt()
        
        system_instruction = (
            "You are a professional, high-precision synchronous translation engine specializing in "
            "Word-Sense Disambiguation (WSD) and linguistic consistency.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. You MUST translate ONLY the text in <TRANSLATE_TARGET>. Do NOT translate the text in <SURROUNDING_CONTEXT>.\n"
            "2. Use <SURROUNDING_CONTEXT> exclusively to understand the domain, semantic flow, and correct word sense of ambiguous words/homonyms.\n"
            "3. If any Terminology & Word-Sense Disambiguation Anchors are provided below, you MUST follow them strictly.\n"
            "4. Maintain correct grammatical gender, case, and natural phrasing in the target language.\n"
            "5. Output ONLY the raw final translated text. Do NOT include markdown code blocks, conversational greetings, explanations, or quotes."
        )

        if anchors_prompt:
            system_instruction += f"\n\n{anchors_prompt}"

        user_content_parts = []
        if context_history:
            user_content_parts.append(f"<SURROUNDING_CONTEXT>\n{context_history}\n</SURROUNDING_CONTEXT>")
        
        user_content_parts.append(
            f"Translate to target language '{target_lang}':\n"
            f"<TRANSLATE_TARGET>\n{target_text}\n</TRANSLATE_TARGET>"
        )

        return {
            "system_instruction": system_instruction,
            "user_prompt": "\n\n".join(user_content_parts)
        }
