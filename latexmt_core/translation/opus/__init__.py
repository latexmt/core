import numpy as np
from transformers.tokenization_utils import BatchEncoding
import torch
from typing import cast

from latexmt_core.alignment.wordsplit import get_words_and_spans
from latexmt_core.context_logger import ContextLogger, logger_from_kwargs
from latexmt_core.markup_string import Markup, MarkupString
from .model import get_model, get_tokenizer

# type imports
from typing import Any, Optional, Sequence
from transformers import PreTrainedTokenizer, PreTrainedModel
from transformers.models.marian import MarianTokenizer, MarianMTModel
from latexmt_core.alignment import Aligner, AlignmentWord, TokenizedAlignmentWord, words_spans_to_markupstr
from latexmt_core.translation import Translator, StringType, TokenSequence


class OpusTransformersTranslatorAligner(Translator, Aligner):
    __input: BatchEncoding
    __output: Any

    __input_prefix: str = ''
    @property
    def input_prefix(self) -> str:
        return self.__input_prefix
    @input_prefix.setter
    def input_prefix(self, value):
        if value is None:
            value = ''
        if value != '':
            self.__input_prefix = value + '\n'

    __source_markup_spans: Sequence[Markup]
    __target_markup_spans: Sequence[Markup]

    __attentions: torch.Tensor
    __word_alignments: torch.Tensor

    __tokenizer: PreTrainedTokenizer
    __model: PreTrainedModel

    __logger: ContextLogger

    def __init__(self, src_lang: str = 'de', tgt_lang: str = 'en', **kwargs):
        '''
        optional parameters:
        - `logger`: an instance of `ContextLogger`
        - `opus_model_base`: a format string used to derive the model checkpoint;
          default: `Helsinki-NLP/opus-mt-de-en`;
          see also `model.py`
        - `opus_input_prefix`: a prefix to be added to the input, for multilingual translation models;
          e.g. `>>ita<<`;
          implicitly includes a newline
        '''

        super().__init__(src_lang, tgt_lang)

        # optionally set up alternative model
        model_base: Optional[str] = kwargs.pop('opus_model_base', None)

        # optionally set up input prefix
        self.input_prefix = kwargs.pop('opus_input_prefix', '')
        if self.input_prefix != '':
            self.input_prefix += '\n'

        self.__logger = logger_from_kwargs(**kwargs)
        self.__logger.debug('Initialising %s (%s -> %s) with model_base=%s' %
                            (self.__class__.__name__, src_lang, tgt_lang, model_base))
        self.__model = get_model(src_lang, tgt_lang, model_base)
        self.__tokenizer = get_tokenizer(src_lang, tgt_lang, model_base)

    def __tokenize_words(self, text: StringType, all_tokens: Optional[TokenSequence] = None) \
            -> tuple[Sequence[TokenizedAlignmentWord], Sequence[Markup], dict[int, int], TokenSequence]:
        '''
        return value:
        - words containing subword tokens and post-whitespace
        - markup spans on a word basis
        - map of subword token indices to word indices
        - tokenisation of the full input text
        '''

        words, markup_spans = get_words_and_spans(text)

        words = [TokenizedAlignmentWord(
            chars=word.chars,
            post_space=word.post_space,
            tokens=[]) for word in words]

        if all_tokens is None:
            all_tokens = cast(TokenSequence,
                              self.__tokenizer(str(text))['input_ids'])

        token_to_word_idx = dict[int, int]()
        tok_idx = 0
        for word_idx, word in enumerate(words):
            word_tokens = []

            while tok_idx < len(all_tokens):
                word_tokens.append(all_tokens[tok_idx])
                token_to_word_idx[tok_idx] = word_idx
                tok_idx += 1

                testdecode = self.__tokenizer.decode(word_tokens)
                # some single tokens (such as 2986) contain punctuation (which
                # we consider "space characters") in addition to word characters
                if not (word.chars + word.post_space).startswith(testdecode):
                    word_tokens.clear()
                    token_to_word_idx.pop(tok_idx-1)
                elif testdecode == word.chars or testdecode == (word.chars + word.post_space).strip():
                    word.tokens = word_tokens
                    break

            # while tok_idx
        # for word_idx, word

        return words, markup_spans, token_to_word_idx, all_tokens

    def __tokenize(self, text: StringType):
        self.__logger.debug('Tokenising input text')

        self.__source_words, self.__source_markup_spans, self.__in_token_to_word_idx, input_tokens = \
            self.__tokenize_words(self.input_prefix + text)

        self.__input = BatchEncoding(
            {'input_ids': [input_tokens],
                'attention_mask': [[1] * len(input_tokens)]},
            tensor_type='pt')

        self.__logger.debug('Done tokenising')

    def __set_output(self):
        self.__logger.debug('Passing input to model',
                            extra={'input_text': self.input_text, 'input_tokens': self.source_words})
        self.__output = self.__model.generate(**self.__input,  # type: ignore
                                              num_beams=8,
                                              num_return_sequences=1,
                                              # early_stopping=True,
                                              # this seems to cause tokens to be lost sometimes ??
                                              # e.g. '#1_ #2_ #3_ #4_ mit #5_' -> '#2_ #3_ #4_ with #5_'
                                              return_dict_in_generate=True,
                                              output_attentions=True)
        self.__logger.debug('Done translating',
                            extra={'output_text': self.output_text})

    def __set_attentions(self):
        self.__logger.debug('Obtaining alignments via attention')

        # this seems to give the best results
        layer = 5
        beam = 0
        head = 0

        cross_attentions = self.__output['cross_attentions']

        num_in = len(cross_attentions)
        num_out = cross_attentions[0][layer].shape[3]

        # rows: output tokens; columns: input tokens
        attention_matrix = torch.zeros(
            size=(num_in, num_out),
            dtype=cross_attentions[0][layer].dtype)

        for i, attention in enumerate(cross_attentions):
            attention = attention[layer]
            out_attention = attention[
                beam, head,
                0,  # (always 0)
                :   # attention weights per output token
            ]

            attention_matrix[i, :] = out_attention

        self.__attentions = attention_matrix

    @property
    def is_marian(self) -> bool:
        return isinstance(self.__model, MarianMTModel)

    @property
    def __input_tokens(self) -> torch.Tensor:
        return cast(torch.Tensor, self.__input['input_ids'])\
            .type(torch.int32)[0, :-1]

    @property
    def __output_tokens(self) -> torch.Tensor:
        return cast(torch.Tensor, self.__output['sequences'])\
            .type(torch.int32)[0, 1:-1]

    @property
    def input_tokens(self) -> TokenSequence:
        return self.__input_tokens.to('cpu').tolist()

    @property
    def input_text(self) -> str:
        return self.__tokenizer.decode(self.__input_tokens, skip_special_tokens=True)

    @property
    def output_tokens(self) -> TokenSequence:
        return self.__output_tokens.to('cpu').tolist()

    @property
    def output_text(self) -> str:
        return self.__tokenizer.decode(self.__output_tokens, skip_special_tokens=True)

    def translate(self, input_text: StringType, glossary: dict[str, str] = {}):
        with self.__logger.frame({'input_text': input_text}):
            self.__logger.debug('Translating input text')
            self.__tokenize(self.input_prefix + input_text)
        self.__input = self.__input.to(self.__model.device)
        self.__set_output()

    @property
    def source_words(self) -> Sequence[AlignmentWord]:
        return self.__source_words

    @property
    def source_markup_spans(self) -> Sequence[Markup]:
        return self.__source_markup_spans

    @property
    def source_text(self) -> MarkupString:
        return words_spans_to_markupstr(self.source_words, self.source_markup_spans)

    @property
    def target_words(self) -> Sequence[AlignmentWord]:
        return self.__target_words

    @property
    def target_markup_spans(self) -> Sequence[Markup]:
        return self.__target_markup_spans

    @property
    def target_text(self) -> MarkupString:
        return words_spans_to_markupstr(self.target_words, self.target_markup_spans)

    @property
    def alignments(self) -> np.ndarray:
        return self.__word_alignments.numpy()

    def align(self, source_text: StringType, target_text: StringType):
        if not self.is_marian:
            self.__logger.warning(
                'Cannot guarantee useful alignments with non-MarianMT models!')

        self.__set_attentions()

        self.__target_words, _, self.__out_token_to_word_idx, _ = \
            self.__tokenize_words(self.output_text,
                                  all_tokens=self.output_tokens)

        threshold = 0.3
        self.__word_alignments = torch.zeros(
            size=(len(self.__target_words), len(self.__source_words)),
            dtype=torch.int8)
        for o_tok, i_tok in torch.nonzero(self.__attentions[:-2, :-1] >= threshold):
            i_tok, o_tok = int(i_tok.item()), int(o_tok.item())
            # no word corresponds to this token in either the input or the output
            if i_tok not in self.__in_token_to_word_idx \
                    or o_tok not in self.__out_token_to_word_idx:
                continue
            i_word = self.__in_token_to_word_idx[i_tok]
            o_word = self.__out_token_to_word_idx[o_tok]
            self.__word_alignments[o_word, i_word] = 1
        # for o_tok, i_tok
        self.__logger.debug('Done aligning')

        self.__target_markup_spans = self._map_markup_spans()
        self.__logger.debug('Done reinserting markup')
