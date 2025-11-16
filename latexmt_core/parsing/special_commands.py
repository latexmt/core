separator_macros = [
    'chapter',
    'section',
    'subsection',
    'paragraph',
    'item',
]

nontext_macros = [
    'ref',
    'autoref',
    'url',
    'cite',
    'citep',
    'citet',
    'citeauthor',
    'citeyear',
    'maketitle',
    'includegraphics',
]

translate_macro_args = {
    'chapter': (2,),
    'section': (2,),
    'subsection': (2,),
    'paragraph': (0,),
    'text': (0,),
    'caption': (0,),
    'title': (0,1,),
}

env_denylist = [
    'lstlisting',
    'verbatim',
    'tikzpicture',
    'tabular',
    'boxproof',
    'figure',
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
