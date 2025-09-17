from dataclasses import dataclass
from typing import cast

# type imports
import pylatexenc.latexnodes.nodes as lw
from latexmt_core.markup_string import MarkupString
from latexmt_core.parsing.to_text import mask_str_default, get_mask_format_str
from typing import Iterable


@dataclass
class TextItem:
    pos: int
    text: MarkupString
    nodelist: list[lw.LatexNode]
    masked_nodes: list[lw.LatexNode]
    parent_nodelist: list[lw.LatexNode]
    mask_str: str = mask_str_default

    def unmask_text(self, text: str) -> str:
        return_text = text
        for mask_idx, mask_node in enumerate(self.masked_nodes):
            mask_idx += 1
            return_text = return_text.replace(get_mask_format_str(self.mask_str).format(
                idx=mask_idx), mask_node.latex_verbatim())

        return return_text

    def __node_is_markup(self, node) -> bool:
        return type(node) in [lw.LatexMacroNode, lw.LatexGroupNode] \
            and node not in self.masked_nodes

    def has_markup(self) -> bool:
        '''
        check if the textitem contains any markup nodes - e.g. `\\emph`,
        `\\textbf`

        markup nodes are macro nodes containing text that is considered to be
        part of the text content, i.e. those macros which are not masked
        '''
        return any(self.__node_is_markup(node) for node in self.nodelist)

    def get_markup_nodes(self) -> Iterable[lw.LatexMacroNode | lw.LatexGroupNode]:
        return cast(filter[lw.LatexMacroNode | lw.LatexGroupNode],
                    filter(self.__node_is_markup, self.nodelist))
