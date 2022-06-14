import json
import logging
import os
import typing as t

from app.classes.shared.console import Console

logger = logging.getLogger(__name__)


class Translation:
    def __init__(self, helper):
        self.helper = helper
        self.translations_path = os.path.join(
            self.helper.root_dir, "app", "translations"
        )
        self.cached_translation = None
        self.cached_translation_lang = None

    def get_language_file(self, language: str):
        return os.path.join(self.translations_path, str(language) + ".json")

    def translate(self, page, word, language):
        fallback_language = "en_EN"

        translated_word = self.translate_inner(page, word, language)
        if translated_word is None:
            translated_word = self.translate_inner(page, word, fallback_language)

        if translated_word:
            if isinstance(translated_word, dict):
                # JSON objects
                return json.dumps(translated_word)
            if isinstance(translated_word, str):
                # Basic strings
                return translated_word
            if hasattr(translated_word, "__iter__"):
                # Multiline strings
                return "\n".join(translated_word)
        return "Error while getting translation"

    def translate_inner(self, page, word, language) -> t.Union[t.Any, None]:
        language_file = self.get_language_file(language)
        try:
            if not self.cached_translation:
                with open(language_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cached_translation = data
            elif self.cached_translation_lang != language:
                with open(language_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cached_translation = data
                    self.cached_translation_lang = language
            else:
                data = self.cached_translation

            try:
                translated_page = data[page]
            except KeyError:
                logger.error(
                    f"Translation File Error: page {page} "
                    f"does not exist for lang {language}"
                )
                Console.error(
                    f"Translation File Error: page {page} "
                    f"does not exist for lang {language}"
                )
                return None

            try:
                translated_word = translated_page[word]
                return translated_word
            except KeyError:
                logger.error(
                    f"Translation File Error: word {word} does not exist on page "
                    f"{page} for lang {language}"
                )
                Console.error(
                    f"Translation File Error: word {word} does not exist on page "
                    f"{page} for lang {language}"
                )
                return None

        except Exception as e:
            logger.critical(
                f"Translation File Error: Unable to read {language_file} due to {e}"
            )
            Console.critical(
                f"Translation File Error: Unable to read {language_file} due to {e}"
            )
            return None
