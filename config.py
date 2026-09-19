import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".context_hud_translator"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "auto",  # auto, gemini, groq, deepl, offline
    "source_lang": "ru",
    "target_lang": "en",
    "debounce_ms": 400,
    "api_keys": {
        "gemini": "",
        "groq": "",
        "deepl": ""
    },
    "hotkeys": {
        "toggle_hud": "<ctrl>+space",
        "quick_replace": "<ctrl>+<shift>+t",
        "double_ctrl_c": True
    },
    "hud": {
        "opacity": 0.94,
        "width": 460,
        "height": 280,
        "always_on_top": True,
        "auto_copy_on_quick_select": False,
        "show_wsd_tags": True
    },
    "wsd": {
        "max_context_sentences": 3,
        "persist_session_anchors": True
    }
}

class AppConfig:
    def __init__(self):
        self.data: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._deep_update(self.data, loaded)
        except Exception as e:
            print(f"[Config] Error loading config: {e}")

    def save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def _deep_update(self, target: dict, source: dict):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._deep_update(target[k], v)
            else:
                target[k] = v

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key_path: str, value: Any):
        keys = key_path.split(".")
        val = self.data
        for k in keys[:-1]:
            if k not in val or not isinstance(val[k], dict):
                val[k] = {}
            val = val[k]
        val[keys[-1]] = value
        self.save()

config = AppConfig()
