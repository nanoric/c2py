import ast
import re
from dataclasses import dataclass
from typing import Union

"""
# https://en.cppreference.com/w/cpp/language/integer_literal
42          - dec
0b101010    - bin
052         - oct
0xaa        - hex
0Xaa        - hex
1234u       - suffix
1234ull     - suffix
145'920     - with single quotes
1.0         - double
1.0f        - float

ignore:
5.9604644775390625e-8F16
'123123'

unsuportted:
1e10        - science
1E10        - science
1e+10
1e-10
1E-10
1E+10

"""
cpp_digit_re = re.compile(
    r"^(0b[01]+|0[0-7]+|0[Xx][0-9a-fA-F]+|[0-9']*[0-9]+)((ull)|(ULL)|(llu)|(LLU)|(ul)|(UL)|(ll)|(LL)|[UuLl])?$"
)

"""
# https://en.cppreference.com/w/cpp/language/string_literal
"asdf"
L"asdfas"
u"asdfasfd"
U"asdfasdf"
u8"asdfasdf"
R"asdf(string!!!)asdf"
u8R"asdf(string!!!)asdf"

parcial:
"asdf"asdf"

"""
cpp_string_re = re.compile(
    r'^(L|u8|u|U)?"(.*)"$'
)
cpp_raw_string_re = re.compile(
    r'^(L|u8|u|U)?R"(?P<delimiter>\w*?)\((.*?)\)(?P=delimiter)"$'
)

# https://en.cppreference.com/w/cpp/language/character_literal
cpp_char_re = re.compile(
    r"^(L|u8|u|U)?'(.+)'$"
)

cpp_digit_suffix_types = {
    None: 'int',
    "": 'int',
    "u": "unsigned int",
    "l": "long",
    "ul": "usngined long",
    "ll": "long long",
    "ull": "unsigned long long",
    "llu": "unsigned long long",
    "f": "float",
}
cpp_digit_suffix_types.update(
    {k.upper(): v for k, v in cpp_digit_suffix_types.items() if k}
)

cpp_string_prefix_types = {
    None: "const char *",
    "": "const char *",
    'u8': "const char8_t *",
    'u': "const char16_t *",
    'U': "const char32_t *",
}

cpp_char_prefix_types = {
    None: "char",
    "": "char",
    'u8': "char8_t",
    'u': "char16_t",
    'U': "char32_t",
}
cpp_char_prefix_max_length = {
    None: 2,
    "": 2,
    'u8': 2,
    'u': 4,
    'U': 8,
}


@dataclass()
class CppLiteral:
    value: Union[int, str, bool]
    literal: str
    cpp_type: str


def _try_parse_cpp_digit_literal(literal: str):
    """
    >>> _try_parse_cpp_digit_literal('100')
    CppLiteral(value=100, literal='100', cpp_type='int')
    >>> _try_parse_cpp_digit_literal('"100"')
    >>> _try_parse_cpp_digit_literal("'100'")
    """
    m = cpp_digit_re.match(literal)
    if not m:
        return None

    value = m.group(1)
    suffix = m.group(2)
    val = ast.literal_eval(value.replace("'", ""))
    t = cpp_digit_suffix_types[suffix]
    return CppLiteral(
        cpp_type=t, value=val, literal=literal
    )


def _try_parse_cpp_string_literal(literal: str):
    """
    >>> _try_parse_cpp_string_literal('"123"')
    CppLiteral(value='123', literal='"123"', cpp_type='const char *')
    >>> _try_parse_cpp_string_literal('R"(123)"')
    CppLiteral(value='123', literal='R"(123)"', cpp_type='const char *')
    >>> _try_parse_cpp_string_literal('R"(1"23)"')
    CppLiteral(value='1"23', literal='R"(1"23)"', cpp_type='const char *')
    """
    m = cpp_string_re.match(literal)
    if m:
        prefix = m.group(1)
        raw = m.group(2)
        to_eval = f'"{raw}"'
        val = ast.literal_eval(to_eval)
    else:
        m = cpp_raw_string_re.match(literal)
        if m:
            prefix = m.group(1)
            raw = m.group(3)
            to_eval = f'r"""{raw}"""'
            val = ast.literal_eval(to_eval)
        else:
            return None

    t = cpp_string_prefix_types[prefix]
    return CppLiteral(
        cpp_type=t, value=val, literal=literal
    )


def _try_parse_cpp_char_literal(literal: str):
    """
    >>> _try_parse_cpp_char_literal("'1'")
    CppLiteral(value='1', literal="'1'", cpp_type='char')
    >>> _try_parse_cpp_char_literal("u8'1'")
    CppLiteral(value='1', literal="u8'1'", cpp_type='char8_t')
    >>> _try_parse_cpp_char_literal("'12'")
    CppLiteral(value='21', literal="'12'", cpp_type='char')
    >>> _try_parse_cpp_char_literal("'123'")
    """
    m = cpp_char_re.match(literal)
    if not m:
        return
    prefix = m.group(1)
    raw = m.group(2)
    raw = raw[::-1]
    if len(raw) > cpp_char_prefix_max_length[prefix]:
        return None

    to_eval = f'"{raw}"'
    val = ast.literal_eval(to_eval)

    t = cpp_char_prefix_types[prefix]
    return CppLiteral(
        cpp_type=t, value=val, literal=literal
    )
