import requests

from context_logger import ContextLogger, logger_from_kwargs
from translation import Translator

# type imports
from translation import StringType, TokenSequence


class OpusHFInferenceTranslator(Translator):
    __api_url: str = 'https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-{src}-{tgt}'
    __api_token: str

    __logger: ContextLogger

    __input_text: str
    __output: dict

    def __init__(self, src_lang: str, tgt_lang: str, **kwargs):
        super().__init__(src_lang, tgt_lang)

        self.__logger = logger_from_kwargs(**kwargs)
        self.__logger.debug('Initialising %s (%s -> %s)' %
                            (self.__class__.__name__, src_lang, tgt_lang))

        self.__api_url = self.__api_url.format(src=src_lang, tgt=tgt_lang)

        from .api_token import get_api_token
        self.__api_token = get_api_token()

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
        return self.__output[0]['translation_text']

    def translate(self, input_text: StringType, glossary: dict[str, str] = {}):
        self.__input_text = str(input_text)

        response = requests.post(
            self.__api_url,
            headers={
                'Authorization': f'Bearer {self.__api_token}'
            },
            json={
                'inputs': self.__input_text,
            }
        )
        self.__output = response.json()

        self.__logger.debug('Got HF Inference API result',
                            extra={'result': self.__output})
