import re
from typing import overload

# type imports
from latexmt_core.glossary import Glossary
from latexmt_core.markup_string import MarkupString
from latexmt_core.translation import StringType


@overload
def apply(text: str, glossary: Glossary) -> str: ...


@overload
def apply(text: MarkupString, glossary: Glossary) -> MarkupString: ...


def apply(text: StringType, glossary: Glossary) -> StringType:
    # glossary enforcement via source replacement
    for source in glossary:
        pat = f'([^\\w#_]+|^)({source})([^\\w#_]|$)'
        instances = list[str]()
        for match in re.finditer(pat, str(text), flags=re.IGNORECASE):
            target = glossary[source]

            pre_punctuation = match.group(1)[:1]

            # capitalise if at start of sentence or paragraph
            if len(match.group(1)) == 0 or match.group(2)[0].isupper() and pre_punctuation in ['.', '!', '?']:
                target = target[0].upper() + target[1:]

            instances.append(match.expand(f'\\1{target}\\3'))
        # for match

        init_repl = '¬UNIQUEMARKER¬'
        if isinstance(text, MarkupString):
            text = text.re_sub(
                pat, init_repl, flags=re.IGNORECASE)
            for final_repl in instances:
                text = text.re_sub(
                    init_repl, final_repl, count=1)
        else:
            text = re.sub(
                pat, init_repl, text, flags=re.IGNORECASE)
            for final_repl in instances:
                text = re.sub(
                    init_repl, final_repl, text, count=1)
    # for source

    return text
