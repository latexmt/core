from typing import cast

from latexmt_core.context_logger import logger_from_kwargs
from latexmt_core.translation import Translator
from latexmt_core.alignment import Aligner


def get_translator_aligner(src_lang: str, tgt_lang: str,
                           trans_type: str, align_type: str | None,
                           **kwargs) -> tuple[Translator, Aligner]:
    align_auto = (align_type == 'auto')
    align_type = ((trans_type
                   if trans_type in ['null', 'opus']
                   else 'awesome')
                  if align_type == 'auto'
                  else align_type)

    logger = logger_from_kwargs(**kwargs)
    kwargs.pop('logger', None)

    logger.info(f'Initialising translator...', extra=kwargs | {
                'trans_type': trans_type, 'src_lang': src_lang, 'tgt_lang': tgt_lang})

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

    logger.info(f'Initialising aligner...',
                extra=kwargs | {'align_type': align_type})
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
                translator = cast(
                    OpusTransformersTranslatorAligner, translator)

                if translator.is_marian:
                    aligner = translator
                elif align_auto:
                    logger.info(
                        'Non-MarianMT translation model; falling back to awesome-align')
                    from latexmt_core.alignment.awesome_align import AwesomeAligner
                    aligner = AwesomeAligner(src_lang, tgt_lang, **kwargs)
                else:
                    raise ValueError(
                        'Opus aligner may only be used with MarianMT model')

            else:
                raise ValueError(
                    'Opus aligner may only be used with Opus translator')

        case 'awesome':
            from latexmt_core.alignment.awesome_align import AwesomeAligner
            aligner = AwesomeAligner(src_lang, tgt_lang, **kwargs)

        case _:
            raise NotImplementedError(f'Invalid aligner: {align_type}')  # nopep8

    return translator, aligner
