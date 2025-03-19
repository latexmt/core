from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from typing import cast

# type imports
from typing import Optional
from transformers.models.marian import MarianTokenizer, MarianMTModel

__srclang: Optional[str] = None
__tgtlang: Optional[str] = None
__model_base: Optional[str] = None
__model: Optional[MarianMTModel] = None
__tokenizer: Optional[MarianTokenizer] = None


def get_model_checkpoint(model_base: str = 'Helsinki-NLP/opus-mt-{src}-{tgt}') -> str:
    '''
    `model_base` may be a formatable string (containing `{src}/{tgt}` as
    placeholders for source and target languages, respectively)

    see the default value for reference
    '''

    return model_base.format(src=__srclang, tgt=__tgtlang)


def update_model(source: str, target: str, model_base: Optional[str] = None):
    global __srclang, __tgtlang, __model_base, __model, __tokenizer

    if source != __srclang or target != __tgtlang or model_base != __model_base:
        __srclang, __tgtlang, __model_base = source, target, model_base
        model_checkpoint = get_model_checkpoint(model_base) \
            if model_base is not None \
            else get_model_checkpoint()
        __tokenizer = cast(MarianTokenizer,
                           AutoTokenizer.from_pretrained(model_checkpoint))
        __model = cast(MarianMTModel,
                       AutoModelForSeq2SeqLM.from_pretrained(model_checkpoint))
        if torch.cuda.is_available():
            __model = __model.to('cuda')  # type: ignore


def get_tokenizer(source: str = 'de', target: str = 'en', model_base: Optional[str] = None) -> MarianTokenizer:
    update_model(source, target, model_base)
    assert __tokenizer is not None
    return __tokenizer


def get_model(source: str = 'de', target: str = 'en', model_base: Optional[str] = None) -> MarianMTModel:
    update_model(source, target, model_base)
    assert __model is not None
    return __model
