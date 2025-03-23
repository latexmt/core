from datetime import datetime
from openai import OpenAI
import os

from latexmt_core.context_logger import ContextLogger, logger_from_kwargs
from latexmt_core.translation import Translator

# type imports
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from latexmt_core.translation import StringType, TokenSequence


def get_api_token():
    try:
        return os.environ['OPENAI_API_TOKEN']
    except Exception:
        raise ValueError(('OpenAI API Token must be provided via the environment'
                          'variable OPENAI_API_TOKEN'))


class OpenAITranslator(Translator):
    __openai_client: OpenAI

    __model: str
    __prompt = 'Translate the text you receive from {src_lang} to {tgt_lang}, and respond only with the translated output.'
    __glossary_prompt = ('Use the following glossary to guide translation. ' +
                         'One entry per line, source and target term(s) are separated by a comma.\n\n')

    __input_text: str
    __result: ChatCompletion

    __logger: ContextLogger

    def __init__(self, src_lang: str, tgt_lang: str, **kwargs):
        super().__init__(src_lang, tgt_lang)
        self.supports_glossary = True

        self.__model = kwargs.pop('openai_model', 'gpt-4o')
        self.__prompt = kwargs.pop('openai_prompt', self.__prompt)

        self.__logger = logger_from_kwargs(**kwargs)
        self.__logger.debug('Initialising %s (%s -> %s) with model=%s, prompt=%s' %
                            (self.__class__.__name__, src_lang, tgt_lang, self.__model, self.__prompt))

        self.__openai_client = OpenAI(api_key=get_api_token())

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
        message = self.__result.choices[0].message

        if message.refusal is not None:
            return 'Refused: ' + message.refusal

        assert message.content is not None
        return message.content

    def translate(self, input_text: StringType, glossary: dict[str, str] = {}):
        self.__input_text = str(input_text)

        messages: list[ChatCompletionMessageParam] = [
            {
                'role': 'developer',
                'content': [
                        {
                            'type': 'text',
                            'text': self.__prompt.format(
                                src_lang=self.src_lang.upper(),
                                tgt_lang=self.tgt_lang.upper()
                            )
                        },
                ]
            },
            {
                'role': 'user',
                'content': [
                        {
                            'type': 'text',
                            'text': self.input_text
                        },
                ]
            },
        ]

        if glossary is not None and len(glossary) > 0:
            glossary_str = '\n'.join(f'{src_text},{tgt_text}'
                                     for (src_text, tgt_text)
                                     in glossary.items())
            messages.insert(1, {
                'role': 'developer',
                'content': [
                    {
                        'type': 'text',
                        'text': self.__glossary_prompt + glossary_str
                    }
                ]
            })

        self.__result = self.__openai_client.chat.completions.create(
            model=self.__model,
            messages=messages
        )

        now_str = str(datetime.now()).replace(' ', '_')
        with open(f'/tmp/openai_{now_str}.json', 'w') as file:
            file.write(self.__result.to_json())

        self.__logger.debug('Got OpenAI API result',
                            extra={'result': vars(self.__result)})
