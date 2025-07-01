from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from typing import cast

# type imports
from typing import Optional
from transformers import PreTrainedTokenizer, PreTrainedModel

__loaded_models = dict[str, tuple[PreTrainedTokenizer, PreTrainedModel]]()


def get_model_checkpoint(source: str, target: str, model_base: str = 'Helsinki-NLP/opus-mt-{src}-{tgt}') -> str:
    '''
    `model_base` may be a formatable string (containing `{src}/{tgt}` as
    placeholders for source and target languages, respectively)

    see the default value for reference
    '''

    return model_base.format(src=source, tgt=target)


def update_model(model_checkpoint: str):
    global __loaded_models

    tokenizer = cast(PreTrainedTokenizer,
                     AutoTokenizer.from_pretrained(model_checkpoint))
    model = cast(PreTrainedModel,
                 AutoModelForSeq2SeqLM.from_pretrained(model_checkpoint))
    if torch.cuda.is_available():
        __model = __model.to('cuda')  # type: ignore

    __loaded_models[model_checkpoint] = (tokenizer, model)


def get_tokenizer(source: str = 'de', target: str = 'en', model_base: Optional[str] = None) -> PreTrainedTokenizer:
    model_checkpoint = get_model_checkpoint(source, target, model_base) \
        if model_base is not None \
        else get_model_checkpoint(source, target)

    update_model(model_checkpoint)
    return __loaded_models[model_checkpoint][0]


def get_model(source: str = 'de', target: str = 'en', model_base: Optional[str] = None) -> PreTrainedModel:
    model_checkpoint = get_model_checkpoint(source, target, model_base) \
        if model_base is not None \
        else get_model_checkpoint(source, target)

    update_model(model_checkpoint)
    return __loaded_models[model_checkpoint][1]
