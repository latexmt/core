import logging
from pylatexenc.latexwalker import LatexWalker, get_default_latex_context_db
from pylatexenc.latexnodes import ParsingStateDeltaEnterMathMode
from pylatexenc.latexnodes.parsers import LatexGeneralNodesParser
from typing import cast

from .to_text import nodelist_to_markupstr, is_space_or_masked
from .text_item import TextItem
from .special_commands import separator_macros, translate_macro_args, env_denylist

# type imports
import pylatexenc.latexnodes.nodes as lw
from pylatexenc.macrospec import LatexContextDb
from typing import Optional


def latex_to_nodelist(text: str, latex_context: Optional[LatexContextDb] = None) -> list[lw.LatexNode]:
    walker = LatexWalker(text, latex_context=latex_context)

    nodelist: lw.LatexNodeList = cast(lw.LatexNodeList, walker.parse_content(
        LatexGeneralNodesParser()
    )[0])

    return nodelist.nodelist


def last_node_has_parbreak(nodelist: list[lw.LatexNode]) -> bool:
    return len(nodelist) > 0 and isinstance(nodelist[-1], lw.LatexCharsNode) and nodelist[-1].chars.endswith('\n\n')


def get_textitems(nodelist: list[lw.LatexNode], latex_context: LatexContextDb = get_default_latex_context_db()) -> list[TextItem]:
    logger = logging.getLogger(__name__)

    # list of extracted TextItems to be returned
    textitems = list[TextItem]()

    # list of nodes associated with the next TextItem to be added to the list
    textitem_nodelist = list[lw.LatexEnvironmentNode | lw.LatexNode]()

    # nodes with nested contents found during iteration (e.g. sections)
    # they are recursively processed before `textitems` is returned
    nested_nodes = list[lw.LatexGroupNode | lw.LatexMathNode |
                        lw.LatexEnvironmentNode]()

    def finish_textitem():
        '''
        helper function: package intermediary nodelist into a TextItem to be
        returned, only if the plaintext representation contains more than
        whitespace and non-text macros

        in any case, clear the intermediary nodelist for the next TextItem
        '''

        if len(textitem_nodelist) > 0:
            # use `pylatexenc` built-in functionality for extracting plain text, modified to
            # mask out non-text macros and math environments
            textitem_text, masked_nodes = nodelist_to_markupstr(
                textitem_nodelist)

            if not is_space_or_masked(textitem_text):
                textitems.append(TextItem(
                    pos=cast(int, textitem_nodelist[0].pos),
                    text=textitem_text,
                    nodelist=textitem_nodelist.copy(),
                    masked_nodes=masked_nodes,
                    parent_nodelist=nodelist))

        textitem_nodelist.clear()

    previous_macro: lw.LatexNode | None = None
    for node in nodelist:
        assert node.parsing_state is not None
        if not node.parsing_state.in_math_mode:
            match node:
                case lw.LatexCharsNode():
                    previous_macro = None
                    textitem_nodelist.append(node)

                case lw.LatexGroupNode():
                    # do not recurse into arguments of unknown macros
                    is_probably_argument = (
                        previous_macro is not None and
                        (latex_context.get_macro_spec(previous_macro.macroname)
                         == latex_context.unknown_macro_spec)
                    )

                    if not is_probably_argument:
                        previous_macro = None

                    # treat char-only group nodes and unknown macro arguments as part of the text
                    if is_probably_argument or all(isinstance(node, lw.LatexCharsNode | lw.LatexGroupNode)
                                                   for node in node.nodelist):
                        textitem_nodelist.append(node)
                    else:
                        nested_nodes.append(node)

                # special whitespace, newlines, etc.
                # may want to do something with this later (e.g. in `parsplit`)
                case lw.LatexSpecialsNode():
                    previous_macro = None
                    textitem_nodelist.append(node)

                case lw.LatexMathNode():
                    previous_macro = None
                    # find nested `\text` nodes
                    nested_nodes.append(node)

                    # 'inline' math is treated as part of the text
                    # 'display' math is treated as part of text too
                    if last_node_has_parbreak(textitem_nodelist):
                        finish_textitem()
                    else:
                        textitem_nodelist.append(node)

                case lw.LatexMacroNode():
                    previous_macro = node
                    # translate section titles, etc.
                    if node.macroname in translate_macro_args:
                        for arg_index in translate_macro_args[node.macroname]:
                            try:
                                nested_nodes.append(
                                    node.nodeargd.argnlist[arg_index])
                            except IndexError:
                                logger.warning(f'Could not find macro argument {arg_index} for macro \'' +
                                               f'{node.latex_verbatim()}\'; perhaps a macro definition is missing?')

                    if node.macroname in separator_macros:
                        finish_textitem()
                    else:
                        textitem_nodelist.append(node)

                case lw.LatexEnvironmentNode():
                    previous_macro = None
                    # is this a math environment?
                    if isinstance(node.spec.body_parsing_state_delta, ParsingStateDeltaEnterMathMode):
                        # find nested `\text` nodes
                        nested_nodes.append(node)

                        # 'inline' math is treated as part of the text
                        # 'display' math is treated as part of text too
                        if last_node_has_parbreak(textitem_nodelist):
                            finish_textitem()
                        else:
                            textitem_nodelist.append(node)

                    else:
                        finish_textitem()
                        if node.environmentname not in env_denylist:
                            nested_nodes.append(node)

                # possibly temporary: break text items on comments
                # currently, `replace_nodes` breaks if the nodelist to be replaced is discontinuous
                #   (TODO: emit a warning if that occurs)
                case lw.LatexCommentNode():
                    finish_textitem()
            # match node

        else:
            if isinstance(node, lw.LatexMacroNode) and node.macroname == 'text':
                nested_nodes.append(node.nodeargd.argnlist[0])

    finish_textitem()

    for n in nested_nodes:
        nested_nodelist = n.nodelist
        if isinstance(nested_nodelist, lw.LatexNodeList):
            nested_nodelist = nested_nodelist.nodelist
        textitems.extend(get_textitems(nested_nodelist, latex_context))

    return textitems


if __name__ == '__main__':
    from pprint import pprint
    import sys

    if len(sys.argv) > 1:
        input_filename = sys.argv[1]
    else:
        input_filename = input('Enter input file name: ')

    input_text = open(input_filename, 'r').read()
    nodes = latex_to_nodelist(input_text)
    ti = get_textitems(nodes)

    pprint(ti)
