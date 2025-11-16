# type imports
import pylatexenc.latexnodes.nodes as lw


def nodelist_to_latex(nodelist):
    """
    patching a library bug with re-encoding \\verb macros
    where '|' is just dropped
    """

    def add_args(nodeargd):
        if nodeargd is None or nodeargd.argspec is None or nodeargd.argnlist is None:
            return ""

        delim_start, delim_end = "", ""
        if (
            hasattr(nodeargd, "verbatim_delimiters")
            and nodeargd.verbatim_delimiters is not None
        ):
            delim_start, delim_end = nodeargd.verbatim_delimiters

        argslatex = delim_start
        for argt, argn in zip(nodeargd.argspec, nodeargd.argnlist):
            if argt == "*":
                if argn is not None:
                    argslatex += nodelist_to_latex([argn])
            elif argt == "[":
                if argn is not None:
                    # the node is a group node with '[' delimiter char anyway
                    argslatex += nodelist_to_latex([argn])
            elif argt == "{":
                # either a group node with '{' delimiter char, or single node argument
                argslatex += nodelist_to_latex([argn])
            else:
                raise ValueError("Unknown argument type: {!r}".format(argt))
        argslatex += delim_end
        return argslatex

    latex = ""
    for n in nodelist:
        if n is None:
            continue
        if n.isNodeType(lw.LatexCharsNode):
            latex += n.chars
            continue

        if n.isNodeType(lw.LatexMacroNode):
            latex += r"\%s%s%s" % (
                n.macroname,
                n.macro_post_space,
                add_args(n.nodeargd),
            )
            continue

        if n.isNodeType(lw.LatexSpecialsNode):
            latex += r"%s%s" % (n.specials_chars, add_args(n.nodeargd))
            continue

        if n.isNodeType(lw.LatexCommentNode):
            latex += "%" + n.comment + n.comment_post_space
            continue

        if n.isNodeType(lw.LatexGroupNode):
            latex += n.delimiters[0] + nodelist_to_latex(n.nodelist) + n.delimiters[1]
            continue

        if n.isNodeType(lw.LatexEnvironmentNode):
            latex += r"\begin{%s}%s" % (n.envname, add_args(n.nodeargd))
            latex += nodelist_to_latex(n.nodelist)
            latex += r"\end{%s}" % (n.envname)
            continue

        if n.isNodeType(lw.LatexMathNode):
            latex += n.delimiters[0] + nodelist_to_latex(n.nodelist) + n.delimiters[1]
            continue

        latex += "<[UNKNOWN LATEX NODE: '%s']>" % (n.nodeType().__name__)

    return latex


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
