from pylatexenc.latexwalker import LatexWalker, LatexWalkerParseError
from pylatexenc.latexnodes import LatexTokenReader, LatexToken, ParsingState
from pylatexenc.latexnodes.parsers import LatexParserBase, LatexStandardArgumentParser

# type imports
import pylatexenc.latexnodes.nodes as lw


class InputArgumentParser(LatexStandardArgumentParser):
    '''
    a version of `pylatexenc.latexnodes.parsers.LatexStandardArgumentParser`
    which adds the first argument to an external list

    used to obtain filenames specified within `\\input` and `\\include` macros
    '''

    out_included_files: list[str]

    def __init__(self,
                 out_included_files: list[str],
                 arg_spec='{',
                 return_full_node_list=False,
                 expression_single_token_requiring_arg_is_error=True,
                 allow_pre_space=True,
                 **kwargs):
        self.out_included_files = out_included_files
        super().__init__(arg_spec, return_full_node_list,
                         expression_single_token_requiring_arg_is_error, allow_pre_space, **kwargs)

    def parse(self,
              latex_walker: LatexWalker,
              token_reader: LatexTokenReader,
              parsing_state: ParsingState,
              **kwargs) \
            -> tuple[lw.LatexNode, None]:
        arg_node, parsing_state_delta = super().parse(
            latex_walker, token_reader, parsing_state, **kwargs)
        input_filename: str = arg_node.nodelist[0].chars
        self.out_included_files.append(input_filename)
        return arg_node, parsing_state_delta


def token_to_text(token: LatexToken) -> str:
    ret_str = token.pre_space
    match token.tok:
        case 'macro':
            ret_str += f'\\{token.arg}'
        case 'comment':
            ret_str += f'%{token.arg}'
        case 'begin_environment':
            ret_str += f'\\begin{{{token.arg}}}'
        case 'end_environment':
            ret_str += f'\\end{{{token.arg}}}'
        case 'specials':
            ret_str += token.arg.specials_chars
        case _:
            ret_str += token.arg
    ret_str += token.post_space
    return ret_str


class CharsArgumentParser(LatexParserBase):
    '''
    similar to `pylatexenc.latexnodes.parsers.LatexStandardArgumentParser`, but
    returns the argument as a single `LatexCharsNode` inside a `LatexGroupNode`
    instead of recursively parsing it

    used to parse `\\newenvironment`, as its arguments may well contain
    incomplete LaTeX structures, which otherwise confuse the parser
    '''

    brace_pairs = {
        '{': '}',
        '(': ')',
        '[': ']',
        '<': '>',
    }

    arg_spec: str

    def __init__(self, arg_spec: str = '{'):
        self.arg_spec = arg_spec
        super().__init__()

    def parse(self,
              latex_walker: LatexWalker,
              token_reader: LatexTokenReader,
              parsing_state: ParsingState) \
            -> tuple[lw.LatexNode, None]:

        brace_stack = list[str]()
        pos = token_reader.cur_pos()

        arg_chars = ''
        while True:
            token: LatexToken = token_reader.peek_token(parsing_state)
            if token.tok == 'brace_open':
                brace_stack.append(token.arg)
            elif token.tok == 'brace_close':
                expected = CharsArgumentParser.brace_pairs[brace_stack.pop()]
                if token.arg != expected:
                    raise LatexWalkerParseError(
                        f'brace \'{token.arg}\' at pos={token_reader.cur_pos()} does not match expected brace \'{expected}\'')

            arg_chars += token_to_text(token)
            token_reader.move_past_token(token)

            if len(brace_stack) == 0:
                break
        # while True

        delimiters = (('', '') if arg_chars[0] not in '{['
                      else (arg_chars[0], arg_chars[-1]))
        chars = arg_chars[len(delimiters[0]):len(arg_chars)-len(delimiters[1])]

        pos_end = token_reader.cur_pos()
        return lw.LatexGroupNode(
            [lw.LatexCharsNode(chars=chars,
                               pos=pos+len(delimiters[0]),
                               pos_end=pos_end-len(delimiters[1]),
                               parsing_state=parsing_state)],
            delimiters=delimiters,
            pos=pos,
            pos_end=pos_end,
            parsing_state=parsing_state), None
