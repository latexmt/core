import numpy as np

from latexmt_core.alignment.wordsplit import get_words_and_spans
from latexmt_core.context_logger import ContextLogger, logger_from_kwargs
from latexmt_core.markup_string import MarkupString

# type imports
from typing import Sequence
from latexmt_core.alignment import Aligner, AlignmentWord
from latexmt_core.markup_string import Markup
from latexmt_core.translation import Translator, StringType, TokenSequence


class NullTranslatorAligner(Translator, Aligner):
    __text: StringType
    __glossary: dict[str, str]
    __words: Sequence[AlignmentWord]
    __markup_spans: Sequence[Markup]

    __logger: ContextLogger

    def __init__(self, src_lang: str, tgt_lang: str, **kwargs):
        super().__init__(src_lang, tgt_lang)

        self.__logger = logger_from_kwargs(**kwargs)
        self.__logger.debug('Initialising %s (%s -> %s)' %
                            (self.__class__.__name__, src_lang, tgt_lang))

    @property
    def input_tokens(self) -> TokenSequence:
        return []

    @property
    def input_text(self) -> str:
        return str(self.__text)

    @property
    def output_tokens(self) -> TokenSequence:
        return []

    @property
    def output_text(self) -> str:
        return self.input_text

    def translate(self, input_text: StringType, glossary: dict[str, str] = {}):
        with self.__logger.frame({
            'input_text': input_text,
            'glossary': glossary
        }):
            self.__logger.debug('`.translate` called')

        self.__text = input_text
        self.__glossary = glossary

    @property
    def source_words(self) -> Sequence[AlignmentWord]:
        return self.__words

    @property
    def source_markup_spans(self) -> Sequence[Markup]:
        return self.__markup_spans

    @property
    def source_text(self) -> MarkupString:
        return self.__text if isinstance(self.__text, MarkupString) else MarkupString(self.__text)

    @property
    def target_words(self) -> Sequence[AlignmentWord]:
        return self.source_words

    @property
    def target_markup_spans(self) -> Sequence[Markup]:
        return self.source_markup_spans

    @property
    def target_text(self) -> MarkupString:
        return self.source_text

    @property
    def alignments(self) -> np.ndarray:
        return np.identity(len(self.__words), dtype=int)

    def align(self, source_text: StringType, target_text: StringType):
        self.__words, self.__markup_spans = get_words_and_spans(self.__text)
