from dataclasses import dataclass
import logging
import numpy as np
from typing import cast

# type imports
from typing import Sequence
from abc import ABC
from latexmt_core.markup_string import Markup, MarkupString
from latexmt_core.translation import StringType


@dataclass
class AlignmentWord:
    chars: str
    post_space: str


@dataclass
class TokenizedAlignmentWord(AlignmentWord):
    tokens: list[int]


class Aligner(ABC):
    def __init__(self, src_lang: str, tgt_lang: str):
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang

    @property
    def source_words(self) -> Sequence[AlignmentWord]:
        raise NotImplementedError()

    @property
    def source_markup_spans(self) -> Sequence[Markup]:
        '''
        markup spans for the source text on a per-word basis
        '''
        raise NotImplementedError()

    @property
    def source_text(self) -> MarkupString:
        raise NotImplementedError()

    @property
    def target_words(self) -> Sequence[AlignmentWord]:
        raise NotImplementedError()

    @property
    def target_markup_spans(self) -> Sequence[Markup]:
        '''
        markup spans for the target text on a per-word basis
        '''
        raise NotImplementedError()

    @property
    def target_text(self) -> MarkupString:
        raise NotImplementedError()

    @property
    def alignments(self) -> np.ndarray:
        '''
        word alignment matrix, with rows represesenting output words and columns
        representing input words

        alignments are absolute, either 0 or 1
        '''
        raise NotImplementedError()

    @property
    def alignments_raw(self) -> np.ndarray:
        '''
        word alignment matrix, with rows represesenting output words and columns
        representing input words

        alignments are weights in range [0-1]
        '''
        raise NotImplementedError()

    def align(self, source_text: StringType, target_text: StringType):
        raise NotImplementedError()

    def _get_target_aligned_idxes(self, src_span_start: int, src_span_end: int) -> set[int]:
        target_aligned_idxes = set[int]()
        for in_token_idx in range(src_span_start, src_span_end):
            target_aligned_idxes.update(cast(list[int], np.flatnonzero(
                self.alignments[:, in_token_idx]).tolist()))
        # for in_token_idx

        return target_aligned_idxes

    def _map_markup_spans(self) -> list[Markup]:
        '''
        `aligner`: an `Aligner` instance pre-loaded with an input/output sentence
        pair, markup spans for the source text, and an alignment matrix

        **returns**: a list of markup spans for the target text, mapped from the
        *source text according to the `aligner`'s `alignment` matrix
        '''

        logger = logging.getLogger(__name__)

        target_markup_spans = list[Markup]()
        for src_markup in self.source_markup_spans:
            aligned_token_idxes = self._get_target_aligned_idxes(
                src_markup.start, src_markup.end)
            # for in_token_idx

            aligned_token_idxes = np.sort(np.array(list(aligned_token_idxes)))

            if len(aligned_token_idxes) == 0:
                content_words = self.source_words[src_markup.start:src_markup.end]
                if len(content_words) < 1:
                    content = ''
                else:
                    content = (''.join(word.chars + word.post_space
                                      for word in content_words[:-1])
                               + content_words[-1].chars)

                logger.warning('Could not map markup contents into output',
                               extra={'content': content, 'macroname': src_markup.macroname})
                continue

            consecutive_aligned_token_ranges = np.split(
                aligned_token_idxes,
                np.where(np.diff(aligned_token_idxes) != 1)[0]+1)

            for aligned_range in consecutive_aligned_token_ranges:
                tgt_markup = Markup(
                    src_markup.macroname,
                    start=aligned_range.min().item(),
                    end=aligned_range.max().item() + 1
                )

                target_markup_spans.append(tgt_markup)
            # for aligned_range
        # for macroname, in_span_start, in_span_end

        return target_markup_spans


def words_spans_to_markupstr(words: Sequence[AlignmentWord], markups: Sequence[Markup]) -> MarkupString:
    text = MarkupString(
        ''.join([word.chars + word.post_space for word in words]))

    for markup in markups:
        text_span_start = sum(len(word.chars + word.post_space) for word in
                              words[:markup.start])
        span_words = words[markup.start:markup.end]
        text_span_end = text_span_start \
            + sum(len(word.chars + word.post_space) for word in span_words) \
            - len(span_words[-1].post_space)

        text.add_markup(markup.macroname, text_span_start, text_span_end)
        # for macroname, word_span_start, word_span_end

    return text
