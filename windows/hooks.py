import ctypes
from ctypes import wintypes
import time
import threading
import queue
import re
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
import win32clipboard

from config import config
from core.dictionary import is_cyrillic, translate_phrase_or_tokens, PHRASES_RU_TO_EN

# Win32 Constants
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207

VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_DELETE = 0x2E
VK_HOME = 0x24
VK_END = 0x23
VK_C = 0x43
VK_T = 0x54
VK_V = 0x56

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
LLKHF_INJECTED = 0x0010

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Set proper 64-bit argument and return types for Win32 functions
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, wintypes.HINSTANCE, wintypes.DWORD]

user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]

user32.CallNextHookEx.restype = ctypes.c_long
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]

user32.GetKeyboardLayout.restype = wintypes.HKL
user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]

# Dedicated Queue for Serialized In-place Replacement
_replace_queue: queue.Queue = queue.Queue()
_is_replacing: bool = False

def _replace_worker_loop():
    """Background worker that reliably erases typed word and pastes replacement via clipboard."""
    global _is_replacing
    while True:
        item = _replace_queue.get()
        if item is None:
            break
        backspaces, text = item
        _is_replacing = True
        try:
            # 1. Erase typed characters with Backspaces (instantaneous, no arbitrary delays)
            for _ in range(backspaces):
                user32.keybd_event(VK_BACK, 0, 0, 0)
                user32.keybd_event(VK_BACK, 0, KEYEVENTF_KEYUP, 0)

            # 2. Put replacement text onto clipboard
            for _ in range(5):
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                    break
                except Exception:
                    time.sleep(0.001)

            # 3. Simulate Ctrl + V to paste the translated text
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_V, 0, 0, 0)
            user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass
        finally:
            _is_replacing = False
            _replace_queue.task_done()

_worker_thread = threading.Thread(target=_replace_worker_loop, daemon=True)
_worker_thread.start()

def queue_replace(backspaces: int, text: str):
    """Enqueues an in-place backspace erasure and text paste."""
    _replace_queue.put((backspaces, text))

def simulate_copy():
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

def simulate_paste():
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

def get_char_from_vk(vk: int, scan: int = 0) -> Optional[str]:
    """Accurately decodes characters typed in the active layout."""
    key_state = (ctypes.c_ubyte * 256)()
    if user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
        key_state[VK_SHIFT] = 0x80
    if user32.GetKeyState(0x14) & 1:  # CapsLock
        key_state[0x14] = 0x01

    hwnd = user32.GetForegroundWindow()
    tid = user32.GetWindowThreadProcessId(hwnd, None) if hwnd else 0
    hkl_active = user32.GetKeyboardLayout(tid) if tid else user32.GetKeyboardLayout(0)

    buf = ctypes.create_unicode_buffer(5)
    if hkl_active:
        res = user32.ToUnicodeEx(vk, scan, key_state, buf, 5, 0, hkl_active)
        if res > 0 and buf.value:
            return buf.value

    return None

def is_char_for_source_lang(ch: str, src_lang: str) -> bool:
    """Checks if a character belongs to the configured source language alphabet."""
    if not ch:
        return False
    if src_lang in ("ru", "uk", "be", "kk", "bg", "sr", "ky", "tg"):
        return is_cyrillic(ch)
    elif src_lang == "en":
        return bool(re.match(r"[a-zA-Z]", ch))
    elif src_lang == "auto":
        return ch.isalnum()
    else:
        return ch.isalpha()

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]

LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

LowLevelMouseProc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

def get_cursor_position():
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y

class WinHookWorker(QObject):
    double_ctrl_c_detected = pyqtSignal(int, int)
    toggle_hud_triggered = pyqtSignal()
    in_place_replace_triggered = pyqtSignal()
    live_typing_toggled = pyqtSignal(bool)

    def __init__(self, context_buffer=None, wsd_engine=None):
        super().__init__()
        self.context_buffer = context_buffer
        self.wsd_engine = wsd_engine
        self._hook = None
        self._mouse_hook = None
        self._last_ctrl_c_time = 0.0
        self._running = True

        # Live in-place translation enabled by default
        self.live_typing_enabled = True
        self._typed_chars = []
        self._sentence_words = []
        self._sentence_translated_text = ""
        self._last_src_word = ""
        self._last_trans_word = ""
        self._last_foreground_hwnd = 0

        self._proc = LowLevelKeyboardProc(self._low_level_keyboard_proc)
        self._mouse_proc = LowLevelMouseProc(self._low_level_mouse_proc)

    def _reset_sentence_context(self):
        """Completely clears the accumulated sentence buffer and typed characters."""
        self._typed_chars.clear()
        self._sentence_words.clear()
        self._sentence_translated_text = ""
        self._last_src_word = ""
        self._last_trans_word = ""

    def _is_key_pressed(self, vk: int) -> bool:
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)

    def _low_level_mouse_proc(self, nCode, wParam, lParam):
        try:
            if nCode >= 0 and wParam in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN):
                ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                if not (ms.flags & LLKHF_INJECTED):
                    # Mouse click moved cursor or selected text -> reset context
                    self._reset_sentence_context()
        except Exception:
            pass
        return user32.CallNextHookEx(self._mouse_hook, nCode, wParam, lParam)

    def _low_level_keyboard_proc(self, nCode, wParam, lParam):
        try:
            if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

                # CRITICAL: Ignore self-injected keystrokes to prevent recursive loops
                if kb.flags & LLKHF_INJECTED:
                    return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                # If an in-place paste is actively executing, yield ~1ms for it to finish cleanly
                if _is_replacing:
                    for _ in range(15):
                        if not _is_replacing:
                            break
                        time.sleep(0.001)

                vk = kb.vkCode
                scan = kb.scanCode

                ctrl_pressed = self._is_key_pressed(VK_CONTROL) or self._is_key_pressed(VK_LCONTROL) or self._is_key_pressed(VK_RCONTROL)
                shift_pressed = self._is_key_pressed(VK_SHIFT)
                alt_pressed = bool(user32.GetAsyncKeyState(0x12) & 0x8000)

                # Reset buffer on foreground window switch
                hwnd = user32.GetForegroundWindow()
                if hwnd != self._last_foreground_hwnd:
                    self._last_foreground_hwnd = hwnd
                    self._reset_sentence_context()

                # Hotkey: Alt + T -> Toggle Live In-place translation
                if alt_pressed and vk == VK_T:
                    self.live_typing_enabled = not self.live_typing_enabled
                    self._reset_sentence_context()
                    self.live_typing_toggled.emit(self.live_typing_enabled)
                    return 1

                # Detect shortcuts that modify or select text (Ctrl+A, Ctrl+X, Ctrl+Z, Ctrl+Y, Ctrl+V, Ctrl+Back, Ctrl+Del)
                if ctrl_pressed:
                    if vk in (0x41, 0x58, 0x5A, 0x59, 0x56, VK_BACK, VK_DELETE):
                        self._reset_sentence_context()

                    # 1. Quick Select (2x Ctrl+C)
                    if not shift_pressed and vk == VK_C:
                        now = time.time()
                        if (now - self._last_ctrl_c_time) < 0.45:
                            x, y = get_cursor_position()
                            self.double_ctrl_c_detected.emit(x, y)
                            self._last_ctrl_c_time = 0.0
                        else:
                            self._last_ctrl_c_time = now
                        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                    # 2. Toggle HUD (Ctrl + Space)
                    elif not shift_pressed and vk == VK_SPACE:
                        self.toggle_hud_triggered.emit()
                        return 1

                    # 3. Replace Selected Text (Ctrl + Shift + T)
                    elif shift_pressed and vk == VK_T:
                        self.in_place_replace_triggered.emit()
                        return 1

                # 4. LIVE IN-PLACE TYPING TRANSLATION (with Sliding Sentence Context Window)
                elif self.live_typing_enabled and not ctrl_pressed and not alt_pressed:
                    # Backspace removes last character from current word
                    if vk == VK_BACK:
                        if self._typed_chars:
                            self._typed_chars.pop()
                        else:
                            # User backspaced past the current word -> reset sentence context
                            self._reset_sentence_context()
                        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                    # Navigation and cancellation keys clear the context buffer
                    if vk in (VK_ESCAPE, VK_TAB, VK_LEFT, VK_RIGHT, VK_UP, VK_DOWN, VK_HOME, VK_END, VK_DELETE, 0x21, 0x22):
                        self._reset_sentence_context()
                        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                    # On SPACE: translate the accumulated sentence context
                    if vk == VK_SPACE:
                        if self._typed_chars:
                            src_word = "".join(self._typed_chars)
                            self._typed_chars.clear()

                            self._sentence_words.append(src_word)
                            full_sentence = " ".join(self._sentence_words)

                            anchors = {}
                            if self.context_buffer:
                                for k, v in self.context_buffer.term_anchors.get_anchors().items():
                                    anchors[k] = v.get("translation", "")

                            src_lang = config.get("source_lang", "ru")
                            tgt_lang = config.get("target_lang", "en")

                            trans = translate_phrase_or_tokens(full_sentence, custom_anchors=anchors, sl=src_lang, tl=tgt_lang)
                            is_sentence_match = True
                            if not trans or trans.lower() == full_sentence.lower():
                                # Fallback to single word if full sentence was untranslated
                                trans = translate_phrase_or_tokens(src_word, custom_anchors=anchors, sl=src_lang, tl=tgt_lang)
                                is_sentence_match = False

                            if trans and trans.lower() != full_sentence.lower() and trans.lower() != src_word.lower():
                                trans = trans.rstrip(".?!,:; \u200b")
                                if is_sentence_match and self._sentence_translated_text:
                                    total_bs = len(self._sentence_translated_text) + len(src_word)
                                else:
                                    total_bs = len(src_word)

                                queue_replace(total_bs, trans + " ")
                                self._sentence_translated_text = trans + " "
                                self._last_src_word = src_word.lower()
                                self._last_trans_word = trans

                                if self.context_buffer:
                                    self.context_buffer.add_text_chunks(src_word)

                                # If sentence exceeds 10 words, slide/commit context window
                                if len(self._sentence_words) >= 10:
                                    self._reset_sentence_context()

                                return 1  # consume space key
                            else:
                                self._reset_sentence_context()
                                return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)
                        else:
                            self._reset_sentence_context()

                    # On Punctuation or Enter
                    punct = ""
                    if vk == VK_RETURN:
                        punct = "\n"
                    else:
                        ch = get_char_from_vk(vk, scan)
                        if ch in (".", ",", "!", "?", ":", ";"):
                            punct = ch

                    if punct and (self._typed_chars or self._sentence_words):
                        if self._typed_chars:
                            src_word = "".join(self._typed_chars)
                            self._typed_chars.clear()
                            self._sentence_words.append(src_word)
                            new_len = len(src_word)
                        else:
                            new_len = 0

                        full_sentence = " ".join(self._sentence_words)
                        if punct not in ("\n", ",", ";"):
                            full_sentence += punct

                        anchors = {}
                        if self.context_buffer:
                            for k, v in self.context_buffer.term_anchors.get_anchors().items():
                                anchors[k] = v.get("translation", "")

                        src_lang = config.get("source_lang", "ru")
                        tgt_lang = config.get("target_lang", "en")

                        trans = translate_phrase_or_tokens(full_sentence, custom_anchors=anchors, sl=src_lang, tl=tgt_lang)
                        if trans and trans.lower() != full_sentence.lower():
                            trans = trans.rstrip(".?!,:; \u200b")
                            if self._sentence_translated_text:
                                total_bs = len(self._sentence_translated_text) + new_len
                            else:
                                total_bs = new_len

                            if punct == "\n":
                                queue_replace(total_bs, trans + "\n")
                            else:
                                queue_replace(total_bs, trans + punct + " ")

                            if self.context_buffer:
                                self.context_buffer.add_text_chunks(full_sentence)

                            # Clause/sentence completed by punctuation -> reset context window
                            self._reset_sentence_context()
                            return 1  # consume punctuation / Enter key

                    # Ordinary character
                    ch = get_char_from_vk(vk, scan)
                    src_lang = config.get("source_lang", "ru")
                    if ch and is_char_for_source_lang(ch, src_lang):
                        self._typed_chars.append(ch)
                    elif ch and not ch.isalnum() and ch not in ('-', "'"):
                        self._reset_sentence_context()
        except Exception:
            pass

        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start_hook(self):
        h_mod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._proc,
            h_mod,
            0
        )
        self._mouse_hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL,
            self._mouse_proc,
            h_mod,
            0
        )
        if not self._hook:
            print("[WinHook] Failed to install SetWindowsHookEx")
            return

        msg = wintypes.MSG()
        while self._running:
            bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if bRet == 0 or bRet == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def stop_hook(self):
        self._running = False
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
            self._mouse_hook = None
        user32.PostQuitMessage(0)
        stop_replace_worker()

def stop_replace_worker():
    _replace_queue.put(None)

