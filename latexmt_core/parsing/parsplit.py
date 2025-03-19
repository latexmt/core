import re
from typing import overload

# type imports
from typing import Sequence
from latexmt_core.markup_string import MarkupString


@overload
def whitespace_collate(text: str) -> str:
    ...


@overload
def whitespace_collate(text: MarkupString) -> MarkupString:
    ...


def whitespace_collate(text: str | MarkupString) -> str | MarkupString:
    '''
    keeps only LaTeX-relevant newlines (two or more in a row), replaces single
    newlines with spaces, replaces multiple spaces with just one
    '''

    pat_repl1 = '([^\n])\n([^\n])', '\\1 \\2'  # collate newlines
    pat_repl2 = '[^\\S\\n]+', ' '  # collate horizontal whitespace

    if isinstance(text, MarkupString):
        return text.re_sub(*pat_repl1).re_sub(*pat_repl2)

    return re.sub(*pat_repl2, re.sub(*pat_repl1, text))


@overload
def strip_keep(text: str) -> tuple[str, str, str]:
    ...


@overload
def strip_keep(text: MarkupString) -> tuple[str, MarkupString, str]:
    ...


def strip_keep(text: str | MarkupString) -> tuple[str, str | MarkupString, str]:
    '''
    returns a 3-tuple representing
    - initial whitespace
    - list of paragraphs in the text
    - final whitespace
    '''
    text_stripped = text.strip()
    initial_whitespace_len = text.find(str(text_stripped))
    final_whitespace_len = len(text) \
        - len(text_stripped) \
        - initial_whitespace_len

    initial_whitespace = '' if initial_whitespace_len == 0 else str(
        text[:initial_whitespace_len])
    final_whitespace = '' if final_whitespace_len == 0 else str(
        text[-final_whitespace_len:])

    return initial_whitespace, text_stripped, final_whitespace


@overload
def parsplit(text: str) -> tuple[str, Sequence[str], str]:
    ...


@overload
def parsplit(text: MarkupString) -> tuple[str, Sequence[MarkupString], str]:
    ...


def parsplit(text: str | MarkupString) -> tuple[str, Sequence[str | MarkupString], str]:
    '''
    splits the text into paragraphs according to LaTeX-relevant newlines and
    collates others

    returns a 3-tuple representing
    - initial whitespace
    - list of paragraphs in the text
    - final whitespace
    '''
    paragraphs = list[str | MarkupString]()

    initial_whitespace, text, final_whitespace = strip_keep(text)
    text = whitespace_collate(text)

    while len(text) > 0:
        # find next paragraph break
        m: re.Match | None
        if isinstance(text, MarkupString):
            m = text.re_search('\n{2,}')
        else:
            m = re.search('\n{2,}', text)

        if m is None:  # finish up
            paragraphs.append(text.strip())
            break
        else:  # add next paragraph and continue
            parbreak_start, parbreak_end = m.span()

            pre_parbreak_chars = text[:parbreak_start]
            if len(pre_parbreak_chars) > 0:
                paragraphs.append(pre_parbreak_chars.strip())

            text = text[parbreak_end:]

    return initial_whitespace, paragraphs, final_whitespace
