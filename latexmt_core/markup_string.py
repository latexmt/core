import unicodedata

from dataclasses import dataclass
import sys
from copy import deepcopy
import re

# type imports
from typing import Iterable, LiteralString, SupportsIndex
if sys.version_info.minor < 11:
    from typing_extensions import Self
else:
    from typing import Self
from re import Match


@dataclass
class Markup:
    macroname: str
    start: int
    end: int


@dataclass
class MarkupStartMarker:
    '''
    `macroname == ''` represents a group node
    `macroname != ''` represents a macro node
    '''
    macroname: str


@dataclass
class MarkupEndMarker:
    '''
    `macroname == ''` represents a group node
    `macroname != ''` represents a macro node
    '''
    macroname: str


class MarkupString:
    __string: str
    __markups: list[Markup]

    def __init__(self, string: str, markups: list[Markup] = []):
        self.__string = string
        self.__markups = markups.copy()

    def __add__(self, o: str | Self):
        if isinstance(o, str):
            return MarkupString(self.__string + o, self.__markups.copy())

        return MarkupString(
            self.__string + o.__string,
            self.__markups +
            [Markup(
                macroname=markup.macroname,
                start=markup.start + len(self.__string),
                end=markup.end + len(self.__string))
             for markup in o.__markups]
        )

    def __radd__(self, o: str | Self):
        if isinstance(o, str):
            return MarkupString(
                o + self.__string,
                [Markup(
                    macroname=markup.macroname,
                    start=markup.start + len(o),
                    end=markup.end + len(o))
                 for markup in self.__markups]
            )

        return MarkupString(
            o.__string + self.__string,
            o.__markups +
            [Markup(
                macroname=markup.macroname,
                start=markup.start + len(o.__string),
                end=markup.end + len(o.__string))
             for markup in self.__markups]
        )

    def __len__(self) -> int:
        return self.__string.__len__()

    def __getitem__(self, key: SupportsIndex | slice) -> 'MarkupString':
        # TODO: support slice step
        if isinstance(key, slice):
            start = key.start
            stop = key.stop
        else:
            start = int(key)
            stop = int(key) + 1

        if start is None:
            start = 0
        if stop is None:
            stop = len(self)

        if start < 0:
            start = len(self) + start
        if stop < 0:
            stop = len(self) + stop

        return MarkupString(
            self.__string[key],
            [Markup(
                macroname=markup.macroname,
                start=0 if markup.start - start < 0 else markup.start - start,
                end=stop if markup.end - start > stop else markup.end - start)
             for markup in filter(
                lambda markup: start <= markup.start < stop,
                self.__markups)]
        )

    def __repr__(self):
        return f'MarkupString({self.__string.__repr__()}, {self.__markups})'

    def __str__(self):
        return self.__string.__str__()

    def find(self, *args) -> int:
        if isinstance(args[0], MarkupString):
            return self.__string.find(args[0].__string, *args[1:])
        return self.__string.find(*args)

    def rfind(self, *args) -> int:
        if isinstance(args[0], MarkupString):
            return self.__string.find(args[0].__string, *args[1:])
        return self.__string.rfind(*args)

    def lstrip(self) -> 'MarkupString':
        if len(self) == 0:
            return self
        index = 0
        while index < len(self) and self.__string[index].isspace():
            index += 1

        return self[index:]

    def rstrip(self) -> 'MarkupString':
        if len(self) == 0:
            return self
        index = len(self.__string)
        while index > 1 and self.__string[index-1].isspace():
            index -= 1

        return self[:index]

    def strip(self) -> 'MarkupString':
        return self.lstrip().rstrip()

    def replace(self, old: LiteralString, new: LiteralString, count: SupportsIndex = -1):
        if count == 0:
            return deepcopy(self)
        count = -1 if count.__index__() == 0 else count
        return self.re_sub(re.escape(old), new, int(count))

    def re_search(self, pattern: str, flags=0) -> (Match[str] | None):
        return re.search(pattern, self.__string, flags)

    def re_sub(self, pattern: str, repl: str, count: int = 0, flags: int = 0) -> Self:
        # TODO: support function argument for repl
        ret = deepcopy(self)

        # update string
        ret.__string = re.sub(pattern, repl, ret.__string, count, flags)
        # update markups
        for match in re.finditer(pattern, self.__string):
            count -= 1
            if count == 0:
                break

            start, end = match.span()
            match_len = end - start
            repl_len = len(match.expand(repl))

            if repl_len == match_len:
                continue
            for markup in filter(lambda m: m.start > start, ret.__markups):
                markup.start += repl_len - match_len
            for markup in filter(lambda m: m.end > end, ret.__markups):
                markup.end += repl_len - match_len

        return ret

    def upper(self) -> Self:
        ret = deepcopy(self)
        ret.__string = ret.__string.upper()
        return ret

    def lower(self) -> Self:
        ret = deepcopy(self)
        ret.__string = ret.__string.lower()
        return ret

    def title(self) -> Self:
        ret = deepcopy(self)
        ret.__string = ret.__string.title()
        return ret

    def __markups_at(self, pos: int) -> Iterable[Markup]:
        return filter(lambda markup: markup.start == pos, self.__markups)

    def add_markup(self, macroname: str, start: int, end: int):
        '''
        if multiple markups are added at the same position, markups added later
        are nested inside those added earlier
        '''

        markup = Markup(macroname, start, end)
        index = 0
        while index < len(self.__markups) and self.__markups[index].start <= markup.start:
            index += 1
        self.__markups.insert(index, markup)

    def to_plaintext(self) -> str:
        return self.__string

    def to_markup_list(self) -> list[str | MarkupStartMarker | MarkupEndMarker]:
        nodelist = list[str | MarkupStartMarker | MarkupEndMarker]()

        markup_stack = list[Markup]()

        for pos in range(0, len(self) + 1):
            while len(markup_stack) > 0 and markup_stack[-1].end <= pos:
                nodelist.append(MarkupEndMarker(markup_stack[-1].macroname))
                markup_stack.pop()

            if pos < len(self):
                for markup in self.__markups_at(pos):
                    nodelist.append(MarkupStartMarker(markup.macroname))
                    markup_stack.append(markup)

                while len(markup_stack) > 0 and markup_stack[-1].end <= pos:
                    nodelist.append(MarkupEndMarker(
                        markup_stack[-1].macroname))
                    markup_stack.pop()

                if len(nodelist) == 0 or not isinstance(nodelist[-1], str):
                    nodelist.append(self.__string[pos])
                else:
                    nodelist[-1] += self.__string[pos]

        return nodelist

    def markups(self) -> Iterable[Markup]:
        return self.__markups


# monkeypatch for unicode-char macros
# autopep8: off
normalize_orig = unicodedata.normalize
def normalize_override(form, unistr: str | MarkupString) -> str:
    if isinstance(unistr, MarkupString):
        unistr = str(unistr)
    return normalize_orig(form, unistr)
unicodedata.normalize = normalize_override
# autopep8: on
