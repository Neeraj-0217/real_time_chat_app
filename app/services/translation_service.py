from typing import Optional, Tuple
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
import re


# Ensure deterministic language detection
DetectorFactory.seed = 0


class TranslationService:
    """
    Handles language detection and translation.
    Uses Google Translate via deep-translator (free tier).
    """

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "hi": "Hindi",
        "es": "Spanish",
    }

    def __init__(self):
        self.cache = {}

    def detect_language(self, text: str) -> str:
        """
        Detect language of given text.
        Returns language code or 'en' as fallback.
        """
        try:
            clean_text = self._clean_for_detection(text)

            if len(clean_text) < 3:
                return "en"

            detected = detect(clean_text)

            if detected in self.SUPPORTED_LANGUAGES:
                return detected

            if detected in {"en-us", "en-gb"}:
                return "en"

            return "en"

        except Exception:
            return "en"

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Translate text into target language.
        Returns translated text and detected source language.
        """
        try:
            if not source_language:
                source_language = self.detect_language(text)

            if source_language == target_language:
                return text, source_language

            cache_key = f"{source_language}_{target_language}_{text}"
            if cache_key in self.cache:
                return self.cache[cache_key], source_language

            translator = GoogleTranslator(
                source=source_language,
                target=target_language,
            )

            translated = translator.translate(text)
            self.cache[cache_key] = translated

            return translated, source_language

        except Exception:
            return text, source_language or "en"

    def _clean_for_detection(self, text: str) -> str:
        """Clean text to improve language detection accuracy."""
        text = re.sub(r"http\S+|www.\S+", "", text)
        text = re.sub(r"[^\w\s]", "", text)
        return " ".join(text.split())

    def is_mixed_language(self, text: str) -> bool:
        """
        Detect basic mixed-language usage.
        """
        words = text.split()
        if len(words) < 3:
            return False

        mid = len(words) // 2
        lang1 = self.detect_language(" ".join(words[:mid]))
        lang2 = self.detect_language(" ".join(words[mid:]))

        return lang1 != lang2


translation_service = TranslationService()
