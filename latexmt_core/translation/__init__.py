# type imports
from abc import ABC
from typing import Union, Sequence

# type imports
from latexmt_core.glossary import Glossary
from latexmt_core.markup_string import MarkupString


# typedefs
type StringType = Union[str, MarkupString]
type TokenType = int
type TokenSequence = Sequence[TokenType]


class Translator(ABC):
    src_lang: str
    tgt_lang: str

    supports_glossary: bool

    def __init__(self, src_lang: str, tgt_lang: str):
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.supports_glossary = False

    @property
    def input_tokens(self) -> TokenSequence:
        raise NotImplementedError()

    @property
    def input_text(self) -> str:
        raise NotImplementedError()

    @property
    def output_tokens(self) -> TokenSequence:
        raise NotImplementedError()

    @property
    def output_text(self) -> str:
        raise NotImplementedError()

    def translate(self, input_text: StringType, glossary: Glossary = {}):
        raise NotImplementedError()

    def __repr__(self):
        return f'{self.__class__.__name__}(src_lang={self.src_lang}, tgt_lang={self.tgt_lang})'
