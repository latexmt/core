import re
from typing import cast

from pylatexenc.latex2text import LatexNodes2Text, MacroTextSpec
from pylatexenc.macrospec import LatexContextDb
from pylatexenc.latexnodes import ParsingStateDeltaEnterMathMode

from latexmt_core.context_logger import ContextLogger, logger_from_kwargs
from latexmt_core.markup_string import MarkupString
from .special_commands import nontext_macros

# type imports
import pylatexenc.latexnodes.nodes as lw


mask_format_str = '#{idx}_'
mask_regex = '#(\\d+)_'


class CustomLatexContextDb(LatexContextDb):
    last_node_unknown: bool

    def __init__(self, **kwargs):
        super(CustomLatexContextDb, self).__init__(**kwargs)
        self.last_node_unknown = False

    @staticmethod
    def default():
        db = CustomLatexContextDb()
        from pylatexenc.latex2text._defaultspecs import specs

        for cat, catspecs in specs:
            db.add_context_category(cat,
                                    macros=catspecs['macros'],
                                    environments=catspecs['environments'],
                                    specials=catspecs['specials'])

        return db

    def get_macro_spec(self, macroname, raise_if_not_found=False):
        '''
        copied from `pylatexenc.macrospec.LatexContextDb`, except an internal
        flag is set to reflect whether the last macro encountered is unknown
        '''
        try:
            return self.lookup_chain_maps['macros'][macroname]
        except KeyError:
            self.last_node_unknown = True
            if raise_if_not_found:
                raise
            return self.unknown_macro_spec


class LatexNodes2MaskedText(LatexNodes2Text):
    masked_nodes: list[lw.LatexNode]
    __logger: ContextLogger
    latex_context: CustomLatexContextDb

    def __init__(self, latex_context=None, **kwargs):
        super(LatexNodes2MaskedText, self).__init__(latex_context, **kwargs)
        self.masked_nodes = list()
        self.__logger = logger_from_kwargs(**kwargs)

    @staticmethod
    def mask_nontext_node(node: lw.LatexNode, l2tobj: 'LatexNodes2MaskedText') -> str:
        '''
        called internally by the `totext` instance in `<module>.nodelist_to_text`
        to determine the textual representation of unknown macro nodes, and other
        nodes which should be kept in the output but should NOT be translated

        returns a "translation-safe" representation of the input - aka. one that
        will not be replaced

        this handler is installed for all unknown macro and environment nodes,
        although the latter part is currently unused as we never request the text
        representation of full environments

        TODO: **ensure** that the replacement text is translation-safe
        '''

        l2tobj.masked_nodes.append(node)
        return mask_format_str.format(idx=len(l2tobj.masked_nodes))

    def node_to_text(self, node, prev_node_hint=None, textcol=0):
        '''
        copied from `pylatexenc.latex2text.LatexNodes2Text`, except math nodes,
        as well as group nodes encountered after an unknown macro, are masked
        '''
        if node is not None:
            # unknown macros and their arguments are masked
            if self.latex_context.last_node_unknown and (
                isinstance(node, lw.LatexGroupNode) or
                isinstance(node, lw.LatexCharsNode) and node.chars == '*'
            ):
                return self.mask_nontext_node(node, self)
            else:
                self.latex_context.last_node_unknown = False

            if isinstance(node, lw.LatexMacroNode) and node.macroname in nontext_macros:
                return self.mask_nontext_node(node, self)

            # # macros with no arguments are masked
            # if isinstance(node, lw.LatexMacroNode) and len(node.nodeargd.argspec) == 0:
            #     return self.mask_nontext_node(node, self)

            # math nodes are masked
            if isinstance(node, lw.LatexMathNode):
                return self.mask_nontext_node(node, self)

            # environment nodes are masked
            if isinstance(node, lw.LatexEnvironmentNode):
                # ONLY math environments should ever be handled here
                if not isinstance(node.spec.body_parsing_state_delta, ParsingStateDeltaEnterMathMode):
                    self.__logger.warning(f'node_to_text called on non-math environment',
                                          extra={'environmentname': node.environmentname})

                return self.mask_nontext_node(node, self)

        return super().node_to_text(node, prev_node_hint, textcol)


class LatexNodes2MarkupText(LatexNodes2MaskedText):
    def nodelist_to_text(self, nodelist: list[lw.LatexNode]):
        s = MarkupString('')

        prev_node = None
        for node in nodelist:
            if self._is_bare_macro_node(prev_node) and isinstance(node, lw.LatexCharsNode):
                prev_node = cast(lw.LatexMacroNode, prev_node)

                if not self.strict_latex_spaces['between-macro-and-chars']:
                    s += prev_node.macro_post_space

            last_nl_pos = s.rfind('\n')
            if last_nl_pos != -1:
                textcol = len(s)-last_nl_pos-1
            else:
                textcol = len(s)

            # make some effort to preserve whitespace
            post_space = ''
            if isinstance(node, lw.LatexMacroNode):
                post_space = node.macro_post_space
                node.macro_post_space = ''
            n_s = self.node_to_text(node, textcol=textcol)
            if isinstance(node, lw.LatexMacroNode | lw.LatexGroupNode) and node not in self.masked_nodes:
                # zero-argument macro nodes are not markup
                if not (isinstance(node, lw.LatexMacroNode) and len(node.nodeargd.argspec) == 0):
                    macroname = '' if isinstance(node, lw.LatexGroupNode) \
                        else node.macroname
                    s.add_markup(macroname, len(s), len(s) + len(n_s))
            s += n_s + post_space

            prev_node = node

        return s

    def macro_node_to_text(self, node):
        # get macro behavior definition.
        macroname = node.macroname
        mac = self.latex_context.get_macro_spec(macroname)
        if mac is None:
            # default for unknown macros
            mac = MacroTextSpec('', discard=True)

        def get_macro_str_repl(node, macroname, mac):
            if mac.simplify_repl:
                return self.apply_simplify_repl(node, mac.simplify_repl,
                                                what=r"macro '\%s'" % (macroname))
            if mac.discard:
                return ''
            a = []
            retstr = MarkupString('')
            if node.nodeargd and node.nodeargd.argnlist:
                a = node.nodeargd.argnlist
            for n in a:
                retstr += self._groupnodecontents_to_text(n)
            return retstr

        macrostr = get_macro_str_repl(node, macroname, mac)
        return macrostr


# FIXME: put this in a better place
custom_ctxdb = CustomLatexContextDb.default()
custom_ctxdb.set_unknown_macro_spec(
    MacroTextSpec('', simplify_repl=LatexNodes2MaskedText.mask_nontext_node))
custom_ctxdb.set_unknown_environment_spec(
    MacroTextSpec('', simplify_repl=LatexNodes2MaskedText.mask_nontext_node))
custom_ctxdb.add_context_category(
    'custom',
    prepend=True,
    macros=[
        MacroTextSpec('enquote', simplify_repl='%s')
    ])
custom_ctxdb.add_context_category(
    'masked',
    prepend=True,
    macros=[
        MacroTextSpec(
            'cite', simplify_repl=LatexNodes2MaskedText.mask_nontext_node),
        MacroTextSpec(
            'input', simplify_repl=LatexNodes2MaskedText.mask_nontext_node)
    ])


def nodelist_to_markupstr(nodelist: list[lw.LatexNode]) -> tuple[MarkupString, list[lw.LatexNode]]:
    '''
    rely on `pylatexenc.latex2text`... for now
    this has _some_ issues (e.g. it eats known markup macros such as \\emph)
    it remains to be seen if we find this to be too limiting
    '''
    totext = LatexNodes2MarkupText(latex_context=custom_ctxdb)
    return totext.nodelist_to_text(nodelist), totext.masked_nodes


def nodelist_to_text(nodelist: list[lw.LatexNode]) -> tuple[str, list[lw.LatexNode]]:
    '''
    rely on `pylatexenc.latex2text`... for now
    this has _some_ issues (e.g. it eats known markup macros such as \\emph)
    it remains to be seen if we find this to be too limiting
    '''
    totext = LatexNodes2MaskedText(latex_context=custom_ctxdb)
    return totext.nodelist_to_text(nodelist), totext.masked_nodes


def is_space_or_masked(text: str | MarkupString) -> bool:
    text = re.sub(mask_regex, '', str(text))
    return len(text) == 0 or text.isspace()
