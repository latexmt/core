import requests

from latexmt_core.context_logger import ContextLogger, logger_from_kwargs
from latexmt_core.translation import Translator

# type imports
from latexmt_core.translation import StringType, TokenSequence


class CustomTranslator(Translator):
    __endpoint: str

    __logger: ContextLogger

    __input_text: str
    __output_text: str

    def __init__(self, src_lang: str, tgt_lang: str, endpoint: str = None, **kwargs):
        super().__init__(src_lang, tgt_lang)

        self.__logger = logger_from_kwargs(**kwargs)
        self.__logger.debug('Initialising %s (%s -> %s)' %
                            (self.__class__.__name__, src_lang, tgt_lang))

        if endpoint is None:
            raise ValueError("endpoint must be provided for CustomTranslator")

        self.__endpoint = endpoint

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
        return self.__output_text

    def translate(self, input_text: StringType, glossary: dict[str, str] = {}):
        self.__input_text = str(input_text)

        request_url = f"http://{self.__endpoint}/latexmt"
        try:
            response = requests.post(
                request_url,
                json={
                    "text":  self.__input_text,
                    "src_lang": self.src_lang,
                    "tgt_lang": self.tgt_lang
                },
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            response_dict = response.json()
            
            if 'response' not in response_dict.keys():
                error_detail = response_dict.get('detail', 'Unknown error')
                self.__logger.error(f"Translation API error: {error_detail}")
                raise Exception(f"Translation API error: {error_detail}")

            self.__output_text = response_dict["response"]
            
            self.__logger.debug('Got cluster translation result',
                              extra={'input_text': self.__input_text, 'output': self.__output_text})
            
        except Exception as e:
            self.__logger.error(f"Error during translation request: {e}")
            raise Exception(f"Error during translation request: {e}")