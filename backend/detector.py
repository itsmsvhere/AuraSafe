"""
AuraSafe — detector.py
Multilingual keyword detection engine (EN / Tamil / Tanglish)
Supports: exact match, case-insensitive, basic normalization
"""

import re
import unicodedata
from typing import Optional


class DetectionResult:
    def __init__(self, detected: bool, keyword: str = "", language: str = "", context: str = ""):
        self.detected = detected
        self.keyword = keyword
        self.language = language
        self.context = context  # surrounding snippet

    def __repr__(self):
        if self.detected:
            return f"<DetectionResult MATCH: '{self.keyword}' [{self.language}]>"
        return "<DetectionResult CLEAN>"


class ContentDetector:
    """
    Core detection engine. Config-driven, thread-safe, no external ML.
    """

    def __init__(self, config: dict):
        detection_cfg = config.get("detection", {})
        self.case_sensitive = detection_cfg.get("case_sensitive", False)
        self.normalize = detection_cfg.get("normalize", True)

        self._english   = detection_cfg.get("english_keywords", [])
        self._tamil     = detection_cfg.get("tamil_keywords", [])
        self._tanglish  = detection_cfg.get("tanglish_keywords", [])

        # Pre-compile patterns for performance
        self._patterns = self._compile_patterns()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _normalize_text(self, text: str) -> str:
        """Strip accents, collapse whitespace, handle leet-speak substitutions."""
        # Unicode normalization
        text = unicodedata.normalize("NFKD", text)
        # Leet-speak basic: 0→o, 1→i, 3→e, 4→a, @→a, $→s, !→i
        leet_map = str.maketrans("01346789@$!|", "oieasbtgasi|")
        text = text.translate(leet_map)
        # Collapse spaces / special chars
        text = re.sub(r"[\s\-_\.]+", " ", text)
        return text.strip()

    def _compile_patterns(self) -> list[tuple]:
        """Return list of (pattern, keyword, language) tuples."""
        patterns = []
        flags = 0 if self.case_sensitive else re.IGNORECASE

        def add(keywords, lang):
            for kw in keywords:
                # Escape and build word-boundary-aware pattern
                escaped = re.escape(kw)
                # For Tamil / Tanglish: use lookahead/lookbehind (no \b on unicode)
                if lang in ("tamil", "tanglish"):
                    pat = re.compile(escaped, flags)
                else:
                    pat = re.compile(r"\b" + escaped + r"\b", flags)
                patterns.append((pat, kw, lang))

        add(self._english,  "english")
        add(self._tamil,    "tamil")
        add(self._tanglish, "tanglish")
        return patterns

    def _extract_context(self, text: str, match: re.Match, window: int = 40) -> str:
        start = max(0, match.start() - window)
        end   = min(len(text), match.end() + window)
        snippet = text[start:end].replace("\n", " ")
        return f"…{snippet}…"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def scan(self, text: str) -> DetectionResult:
        """
        Scan text. Returns first DetectionResult with detected=True, or clean result.
        """
        if not text or not text.strip():
            return DetectionResult(False)

        working = self._normalize_text(text) if self.normalize else text

        for pattern, keyword, lang in self._patterns:
            m = pattern.search(working)
            if m:
                ctx = self._extract_context(working, m)
                return DetectionResult(True, keyword, lang, ctx)

        return DetectionResult(False)

    def scan_all(self, text: str) -> list[DetectionResult]:
        """Scan text and return ALL matches (not just first)."""
        if not text or not text.strip():
            return []
        working = self._normalize_text(text) if self.normalize else text
        results = []
        for pattern, keyword, lang in self._patterns:
            for m in pattern.finditer(working):
                ctx = self._extract_context(working, m)
                results.append(DetectionResult(True, keyword, lang, ctx))
        return results

    def reload_config(self, config: dict):
        """Hot-reload keyword lists without restart."""
        detection_cfg = config.get("detection", {})
        self._english  = detection_cfg.get("english_keywords", [])
        self._tamil    = detection_cfg.get("tamil_keywords", [])
        self._tanglish = detection_cfg.get("tanglish_keywords", [])
        self._patterns = self._compile_patterns()
