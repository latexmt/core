separator_macros = [
    'section',
    'item',
    'paragraph'
]

nontext_macros = [
    'ref',
    'autoref',
    'url',
    'cite',
]

translate_macro_args = {
    'section': (2,),
    'text': (0,),
    'caption': (0,),
    'paragraph': (0,),
}

env_denylist = [
    'lstlisting',
    'verbatim',
    'tikzpicture',
    'tabular',
    'boxproof',
]

math_environs = [
    # amsmath
    'subarray',
    'smallmatrix',
    'matrix',
    'cases',
    'subequations',
    'gather',
    'gather*',
    'align',
    'align*',
    'flalign',
    # 'flalign*',
    'alignat',
    'alignat*',
    'xalignat',
    # 'xalignat*',
    'xxalignat',
    'split',
    'multline',
    # 'multline*',
]
