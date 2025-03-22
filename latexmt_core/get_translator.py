from typing import cast

from latexmt_core.context_logger import logger_from_kwargs
from latexmt_core.translation import Translator
from latexmt_core.alignment import Aligner


def get_translator_aligner(src_lang: str, tgt_lang: str,
                           trans_type: str, align_type: str | None,
                           **kwargs) -> tuple[Translator, Aligner]:
    align_type = ((trans_type
                   if trans_type in ['null', 'opus']
                   else 'awesome')
                  if align_type == 'auto'
                  else align_type)

    logger = logger_from_kwargs(**kwargs)
    kwargs.pop('logger', None)

    kwargs.pop('src_lang', None)
    kwargs.pop('tgt_lang', None)
    kwargs.pop('trans_type', None)
    kwargs.pop('align_type', None)

    logger.info(f'Initialising translator for {src_lang}-{tgt_lang}...')  # nopep8

    match trans_type:
        case 'null':
            from latexmt_core.translation.null import NullTranslatorAligner
            translator = NullTranslatorAligner(
                src_lang, tgt_lang, **kwargs)
        case 'opus':
            from latexmt_core.translation.opus import OpusTransformersTranslatorAligner
            translator = OpusTransformersTranslatorAligner(
                src_lang, tgt_lang, **kwargs)
        case 'api_opus':
            from latexmt_core.translation.api_opus import OpusHFInferenceTranslator
            translator = OpusHFInferenceTranslator(
                src_lang, tgt_lang, **kwargs)
        case 'api_deepl':
            from latexmt_core.translation.api_deepl import DeepLTranslator
            translator = DeepLTranslator(
                src_lang, tgt_lang, **kwargs)
        case 'api_openai':
            from latexmt_core.translation.api_openai import OpenAITranslator
            translator = OpenAITranslator(
                src_lang, tgt_lang, **kwargs)
        case _:
            raise NotImplementedError(f'Invalid translator: {trans_type}')  # nopep8

    logger.info(f'Initialising aligner for {src_lang}-{tgt_lang}...')
    match align_type:
        case 'null':
            if trans_type == 'null':
                from latexmt_core.translation.null import NullTranslatorAligner
                aligner = cast(NullTranslatorAligner, translator)
            else:
                raise ValueError(
                    'Null aligner may only be used with Null translator')
        case 'opus':
            if trans_type == 'opus':
                from latexmt_core.translation.opus import OpusTransformersTranslatorAligner
                aligner = cast(OpusTransformersTranslatorAligner, translator)
            else:
                raise ValueError(
                    'Opus aligner may only be used with Opus translator')
        case 'awesome':
            from latexmt_core.alignment.awesome_align import AwesomeAligner
            aligner = AwesomeAligner(src_lang, tgt_lang, **kwargs)
        case _:
            raise NotImplementedError(f'Invalid aligner: {align_type}')  # nopep8

    return translator, aligner
