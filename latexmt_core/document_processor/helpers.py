from itertools import chain
from pylatexenc.macrospec import ParsedMacroArgs
import re
from typing import cast

from latexmt_core.parsing.to_text import get_mask_regex, get_mask_format_str

# type imports
from pathlib import Path
import pylatexenc.latexnodes.nodes as lw
from latexmt_core.parsing.text_item import TextItem
from latexmt_core.markup_string import MarkupStartMarker, MarkupEndMarker


def ensure_dir(dir: Path):
    if dir.is_file():
        raise NotADirectoryError(dir)
    if not dir.exists():
        dir.mkdir(parents=True)


def textitem_flatlist_to_nodelist(
    textitem: TextItem,
    translated_flatlist: list[str | MarkupStartMarker | MarkupEndMarker],
) -> list[lw.LatexNode]:
    translated_nodelist = list[lw.LatexNode]()
    translated_pos: int = cast(int, textitem.nodelist[0].pos)

    nodelist_stack = [translated_nodelist]
    for translated_elem in translated_flatlist:
        match translated_elem:
            # re-insert masked nodes
            case str():
                elem_split = re.split(get_mask_regex(textitem.mask_str), translated_elem)
                for text, mask_idx in zip(elem_split[::2], chain(map(int, elem_split[1::2]), [None])):
                    # special case for percent signs
                    # TODO: other special cases?
                    # TODO: look for a better place to do this
                    text = text.replace('%', '\\%')

                    chars_node = lw.LatexCharsNode(
                        text,
                        pos=translated_pos,
                        len=len(text),
                        parsing_state=textitem.nodelist[0].parsing_state)
                    nodelist_stack[-1].append(chars_node)
                    translated_pos += cast(int, chars_node.len)

                    if mask_idx is not None:
                        try:
                            mask_node = textitem.masked_nodes[mask_idx - 1]
                            mask_node.pos = translated_pos
                        except Exception as e:
                            # TODO: emit warning
                            masked_str = get_mask_format_str(mask_str).format(idx=mask_idx)
                            mask_node = lw.LatexCharsNode(
                                masked_str, len=len(masked_str), pos=translated_pos)

                        nodelist_stack[-1].append(mask_node)
                        translated_pos += cast(int, mask_node.len)

            case MarkupStartMarker(macroname):
                macro_start_len = len(macroname) + 1
                group_node = lw.LatexGroupNode(
                    [],
                    pos=translated_pos + macro_start_len,
                    len=0,
                    parsing_state=textitem.nodelist[0].parsing_state
                )

                if macroname == '':
                    markup_node = group_node
                else:
                    markup_node = lw.LatexMacroNode(
                        translated_elem.macroname,
                        pos=translated_pos,
                        len=0,
                        nodeargd=ParsedMacroArgs(
                            [group_node], argspec='{'),
                        parsing_state=textitem.nodelist[0].parsing_state
                    )
                    translated_pos += macro_start_len + 1

                nodelist_stack[-1].append(markup_node)
                nodelist_stack.append(group_node.nodelist)

            case MarkupEndMarker(macroname):
                nodelist_stack.pop()
                if macroname != '':
                    cast(lw.LatexMacroNode, nodelist_stack[-1][-1])\
                        .nodeargd.argnlist[0].pos_end = translated_pos
                translated_pos += 1
                nodelist_stack[-1][-1].pos_end = translated_pos
    # for translated_elem in translated_flatlist

    return translated_nodelist
