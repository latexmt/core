# re-export
from pylatexenc.latexwalker import nodelist_to_latex

# type imports
import pylatexenc.latexnodes.nodes as lw


def replace_nodes(parent_nodelist: list[lw.LatexNode],
                  orig_nodelist: list[lw.LatexNode],
                  new_nodelist: list[lw.LatexNode]):
    rm_indexes = list(reversed([parent_nodelist[:].index(node)
                                for node in orig_nodelist]))
    start_idx = rm_indexes[-1]

    for idx in rm_indexes:
        parent_nodelist.pop(idx)

    for node in reversed(new_nodelist):
        parent_nodelist.insert(start_idx, node)
