from itertools import chain

# type imports
from typing import Iterable, LiteralString

unicode_repls: dict[Iterable[LiteralString], dict[Iterable[LiteralString], LiteralString]] = {
    # always
    (): {
        ('{\\"A}', '\\"A', '\\"{A}'): 'Ä',
        ('{\\"a}', '\\"a', '\\"{a}'): 'ä',
        ('{\\"O}', '\\"O', '\\"{O}'): 'Ö',
        ('{\\"o}', '\\"o', '\\"{o}'): 'ö',
        ('{\\"U}', '\\"U', '\\"{U}'): 'Ü',
        ('{\\"u}', '\\"u', '\\"{u}'): 'ü',
        ('\\MakeUppercase{\\ss}', '\\MakeUppercase{\\ss{}}'): 'ẞ',
        ('{\\ss}', '\\ss{}'): 'ß',
    },

    ('german', 'ngerman'): {
        ("'A",): 'Ä',
        ("'O",): 'Ö',
        ("'U",): 'Ü',
        ("'a",): 'ä',
        ("'o",): 'ö',
        ("'u",): 'ü',
        ("'s",): 'ß',
    }
}


def get_replacements(packages: Iterable[LiteralString]) -> Iterable[tuple[Iterable[LiteralString], LiteralString]]:
    repl_dict_list = [unicode_repls[()]]

    for repl_pkgs, repl_dict in filter(lambda kv: kv[0] != (), unicode_repls.items()):
        for pkg in repl_pkgs:
            if pkg in packages:
                repl_dict_list.append(repl_dict)
                break
        # for pkg
    # for repl_pkgs, repl_dict

    return chain(*(dict.items() for dict in repl_dict_list))
