import re

from . import AlignmentWord

# type imports
from typing import Iterable
from . import StringType
from latexmt_core.markup_string import Markup, MarkupString, MarkupStartMarker, MarkupEndMarker


def split_words(text: str) -> Iterable[tuple[str, str]]:
    rr = re.split('([^\\w\\(\\)\\[\\]#_\'\"-]+)', text)
    words = rr[::2]
    splits = rr[1::2]
    if len(words[-1]) > 0:
        splits.append('')

    return zip(words, splits)


def get_words_and_spans(text: StringType) -> tuple[list[AlignmentWord], list[Markup]]:
    '''
    return value:
    - words containing subword tokens and post-whitespace
    - markup spans on a word basis
    '''

    words = list[AlignmentWord]()
    markup_spans = list[Markup]()

    if isinstance(text, MarkupString):
        markup_stack = list[int]()

        for elem in text.to_markup_list():
            match elem:
                case MarkupStartMarker():
                    markup_stack.append(len(words))
                case MarkupEndMarker(macroname):
                    start = markup_stack[-1]
                    end = len(words)
                    markup_spans.append(
                        Markup(macroname, start, end))
                    markup_stack.pop()
                case str():
                    for word, whitespace in split_words(elem):
                        if len(word) > 0 or len(words) == 0:
                            words.append(AlignmentWord(
                                chars=word,
                                post_space=whitespace))
                        else:
                            words[-1].post_space += whitespace
        # for elem
    else:
        markup_spans = []
        for word, whitespace in split_words(text):
            words.append(AlignmentWord(
                chars=word,
                post_space=whitespace))
        # for word, whitespace

    return words, markup_spans
