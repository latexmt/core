from datetime import datetime
from deepl import DeepLClient, GlossaryInfo
import json

from latexmt_core.context_logger import ContextLogger, logger_from_kwargs
from latexmt_core.translation import Translator

# type imports
from deepl import TextResult
from typing import Any, Optional
from latexmt_core.translation import StringType, TokenSequence


class DeepLTranslator(Translator):
    __deepl_client: DeepLClient
    __logger: ContextLogger

    __input_text: str
    __result: TextResult

    __cached_glossary: Optional[dict[str, str]]
    __glossary_info: Optional[GlossaryInfo] = None

    def __init__(self, src_lang: str, tgt_lang: str, **kwargs):
        tgt_lang = "en-gb" if tgt_lang == "en" else tgt_lang

        super().__init__(src_lang, tgt_lang)
        self.supports_glossary = True

        self.__logger = logger_from_kwargs(**kwargs)
        self.__logger.debug(
            "Initialising %s (%s -> %s)" % (self.__class__.__name__, src_lang, tgt_lang)
        )

        from .api_token import get_api_token

        self.__deepl_client = DeepLClient(get_api_token())
        self.__cached_glossary = None
        self.__glossary_info = None

    @property
    def input_tokens(self) -> TokenSequence:
        return []

    @property
    def input_text(self) -> str:
        return self.__input_text

    @property
    def output_tokens(self) -> TokenSequence:
        return []

    @property
    def output_text(self) -> str:
        return self.__result.text

    def translate(self, input_text: StringType, glossary: dict[str, str] = {}):
        self.__input_text = str(input_text)

        if len(glossary) > 0 and glossary != self.__cached_glossary:
            self.__cached_glossary = glossary
            self.__glossary_info = self.__deepl_client.create_glossary(
                name="temp_glossary",
                source_lang=self.src_lang,
                target_lang=self.tgt_lang,
                entries=glossary,
            )

        result = self.__deepl_client.translate_text(
            text=self.input_text,
            source_lang=self.src_lang,
            target_lang=self.tgt_lang,
            glossary=self.__glossary_info,
        )

        self.__result = result[0] if isinstance(result, list) else result

        now_str = str(datetime.now()).replace(" ", "_")

        def serialize_text_result(result: TextResult) -> dict[str, Any]:
            return {
                "text": result.text,
                "detected_source_lang": result.detected_source_lang,
                "billed_characters": result.billed_characters,
                "model_type_used": result.model_type_used,
            }

        with open(f"/tmp/deepl_{now_str}.json", "w") as file:
            json.dump(
                serialize_text_result(result)
                if isinstance(result, TextResult)
                else [serialize_text_result(subres) for subres in result],
                file,
            )

        self.__logger.debug(
            "Got DeepL API result", extra={"result": vars(self.__result)}
        )
