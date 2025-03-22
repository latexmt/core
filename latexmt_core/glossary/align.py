import numpy as np
from typing import cast

from latexmt_core.alignment.wordsplit import get_words_and_spans
from latexmt_core.markup_string import Markup

# type imports
from typing import Sequence, Optional
from latexmt_core.alignment import Aligner, AlignmentWord
from latexmt_core.markup_string import MarkupEndMarker, MarkupStartMarker


def merge_words_and_spans[T](target_words: Sequence[T], markups: Sequence[Markup]) \
        -> list[T | MarkupStartMarker | MarkupEndMarker]:
    '''
    mostly a copy of `MarkupString.to_markup_list`
    '''

    merged_list = list[T | MarkupStartMarker | MarkupEndMarker]()

    markup_stack = list[Markup]()
    for pos in range(0, len(target_words) + 1):
        while len(markup_stack) > 0 and markup_stack[-1].end <= pos:
            merged_list.append(MarkupEndMarker(markup_stack[-1].macroname))
            markup_stack.pop()

        if pos < len(target_words):
            for markup in filter(lambda markup: markup.start == pos, markups):
                merged_list.append(MarkupStartMarker(markup.macroname))
                markup_stack.append(markup)

            while len(markup_stack) > 0 and markup_stack[-1].end <= pos:
                merged_list.append(MarkupEndMarker(
                    markup_stack[-1].macroname))
                markup_stack.pop()

            merged_list.append(target_words[pos])

    return merged_list


def apply(aligner: Aligner, glossary: dict[str, str]) -> tuple[Sequence[AlignmentWord], Sequence[Markup]]:
    # glossary enforcement via word alignments
    if len(glossary) == 0:
        return aligner.target_words, aligner.target_markup_spans

    glossary_src_idxes = list[tuple[str, int]]()
    for gloss_src in glossary:
        if gloss_src not in str(aligner.source_text):
            continue

        gloss_src_words, _ = get_words_and_spans(gloss_src)

        for index, wordlist in enumerate(aligner.source_words[idx:idx+len(gloss_src_words)]
                                         for idx
                                         in range(len(aligner.source_words))):
            # should we ignore the case here?
            if all(gloss_src_word.chars.lower() == word.chars.lower()
                    for gloss_src_word, word
                    in zip(gloss_src_words, wordlist)):
                glossary_src_idxes.append((gloss_src, index))
        # for index, wordlist
    # for gloss_src

    target_words, target_spans = get_words_and_spans(aligner.target_text)

    # preserve original indices
    target_words_tmp: list[tuple[int, AlignmentWord]] = list(
        enumerate(target_words))

    tgt_list_tmp: list[tuple[int, AlignmentWord] | MarkupStartMarker | MarkupEndMarker] \
        = merge_words_and_spans(target_words_tmp, target_spans)

    for gloss_src, src_start_idx in glossary_src_idxes:
        gloss_tgt = glossary[gloss_src]
        gloss_src_words, _ = get_words_and_spans(gloss_src)
        gloss_tgt_words, _ = get_words_and_spans(gloss_tgt)

        target_word_idxes: list[int] = sorted(list(
            aligner._get_target_aligned_idxes(
                src_start_idx,
                src_start_idx + len(gloss_src_words)))
        )
        if len(target_word_idxes) == 0:
            # TODO: emit warning
            continue

        # sometimes the alignments are bad; find the most likely sequence of target tokens:
        #   - all consecutive tokens
        #   - position in target text close to position in source text
        # https://stackoverflow.com/a/7353335/18735701
        target_subsequences = np.split(
            target_word_idxes,
            np.where(np.diff(target_word_idxes) != 1)[0]+1
        )

        if len(target_subsequences) > 1:
            # sort by closest distance to original sequence
            target_subsequences = list(
                sorted(target_subsequences,
                       key=lambda arr: np.abs(
                           np.mean(arr - src_start_idx)
                       ).item())
            )
            target_word_idxes = cast(
                list[int], target_subsequences[0].tolist())

        insert_pos = None
        for index in sorted(target_word_idxes):
            try:
                insert_pos = tgt_list_tmp.index(next(filter(
                    lambda i_w:
                        isinstance(i_w, tuple)
                        and i_w[0] == min(target_word_idxes),
                    tgt_list_tmp
                )))
            except:
                pass
        if insert_pos is None:
            # TODO: emit warning
            continue

        try:
            final_post_space = cast(tuple[int, AlignmentWord], next(filter(
                lambda i_w:
                    isinstance(i_w, tuple)
                    and i_w[0] == max(target_word_idxes),
                tgt_list_tmp
            )))[1].post_space
        except StopIteration:
            final_post_space = ' '
        gloss_tgt_words[-1].post_space = final_post_space

        # capitalise if at start of sentence or paragraph
        prev_word_idx = insert_pos - 1
        prev_word: Optional[tuple[int, AlignmentWord]] = None
        while prev_word_idx >= 0 and not isinstance(tgt_list_tmp[prev_word_idx], tuple):
            prev_word_idx -= 1
        prev_word = cast(tuple[int, AlignmentWord],
                         tgt_list_tmp[prev_word_idx])
        if prev_word is None or prev_word[1].post_space[:1] in ['.', '!', '?']:
            gloss_tgt_words[0].chars = gloss_tgt_words[0].chars[0].upper() \
                + gloss_tgt_words[0].chars[1:]

        tgt_list_tmp = list(filter(
            lambda i_w:
                not isinstance(i_w, tuple)
                or i_w[0] not in target_word_idxes,
            tgt_list_tmp
        ))
        tgt_list_tmp = tgt_list_tmp[:insert_pos] \
            + list((-99, w) for w in gloss_tgt_words) \
            + tgt_list_tmp[insert_pos:]
    # for gloss_src

    words: list[AlignmentWord] = list()
    spans: list[Markup] = list()

    markup_stack = list[tuple[str, int]]()
    tmp_idx = 0
    for item in tgt_list_tmp:
        item = item[1] if isinstance(item, tuple) else item
        match item:
            case MarkupStartMarker():
                markup_stack.append((item.macroname, tmp_idx))
            case MarkupEndMarker():
                macroname, start = markup_stack.pop()
                spans.append(Markup(macroname, start, end=tmp_idx))
            case AlignmentWord():
                words.append(item)
                tmp_idx += 1

    return words, spans
