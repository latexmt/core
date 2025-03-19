import numpy as np
from transformers.models.bert import BertTokenizer, BertModel
import torch

# type imports
from typing import Sequence
from latexmt_core.alignment import Aligner, StringType, AlignmentWord, TokenizedAlignmentWord, words_spans_to_markupstr
from latexmt_core.alignment.wordsplit import get_words_and_spans
from latexmt_core.markup_string import Markup, MarkupString


class AwesomeAligner(Aligner):
    '''
    language-agnostic aligner
    '''

    __tokenizer: BertTokenizer
    __model: BertModel

    __source_words: Sequence[TokenizedAlignmentWord]
    __source_markup_spans: Sequence[Markup]

    __target_words: Sequence[TokenizedAlignmentWord]
    __target_markup_spans: Sequence[Markup]

    __subword_alignments: torch.Tensor
    __word_alignments: torch.Tensor

    def __init__(self, src_lang: str, tgt_lang: str, **kwargs):
        model = 'bert-base-multilingual-cased'
        self.__tokenizer = BertTokenizer.from_pretrained(model)
        self.__model = BertModel.from_pretrained(model)  # type: ignore
        if torch.cuda.is_available():
            self.__model = self.__model.to('cuda')  # type: ignore
        super().__init__(src_lang, tgt_lang)

    def __tokenize_words(self, text: StringType) -> tuple[list[TokenizedAlignmentWord], list[Markup], dict[int, int]]:
        '''
        return value:
        - words containing subword tokens and post-whitespace
        - markup spans on a word basis
        - map of subword token indices to word indices
        '''

        words, markup_spans = get_words_and_spans(text)

        words = [TokenizedAlignmentWord(
            chars=word.chars,
            post_space=word.post_space,
            tokens=self.__tokenizer(word.chars)[
                'input_ids'][1:-1]  # type: ignore
        ) for word in words]

        token_to_word_idx = dict[int, int]()
        tok_idx = 0
        for word_idx, word in enumerate(words):
            for _ in word.tokens:
                token_to_word_idx[tok_idx] = word_idx
                tok_idx += 1
        # for word_idx, word

        return words, markup_spans, token_to_word_idx

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
        self.__source_words, self.__source_markup_spans, in_token_to_word_idx = \
            self.__tokenize_words(source_text)
        self.__target_words, _, out_token_to_word_idx = \
            self.__tokenize_words(target_text)

        in_src = torch.IntTensor(
            [[subword for word in self.__source_words for subword in word.tokens]]).to(self.__model.device)
        in_tgt = torch.IntTensor(
            [[subword for word in self.__target_words for subword in word.tokens]]).to(self.__model.device)

        with torch.no_grad():
            align_layer = 8
            out_src = self.__model(in_src, output_hidden_states=True)[
                2][align_layer][0, :]
            out_tgt = self.__model(in_tgt, output_hidden_states=True)[
                2][align_layer][0, :]

            dot_prod = torch.matmul(out_src, out_tgt.transpose(-1, -2))

            softmax_srctgt = torch.nn.Softmax(dim=-1)(dot_prod)
            softmax_tgtsrc = torch.nn.Softmax(dim=-2)(dot_prod)

            threshold = 1e-3
            self.__subword_alignments = ((softmax_srctgt > threshold) *
                                         (softmax_tgtsrc > threshold))

        self.__word_alignments = torch.zeros(
            size=(len(self.__target_words), len(self.__source_words)),
            dtype=torch.int8)
        for i_tok, o_tok in torch.nonzero(self.__subword_alignments):
            i_word = in_token_to_word_idx[int(i_tok.item())]
            o_word = out_token_to_word_idx[int(o_tok.item())]
            self.__word_alignments[o_word, i_word] = 1
        # for i_tok, o_tok

        self.__target_markup_spans = self._map_markup_spans()
