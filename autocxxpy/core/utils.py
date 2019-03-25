import ast
import re
from dataclasses import dataclass

"""
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
    "(0b[01]+|0[0-7]+|0[Xx][0-9a-fA-F]+|[0-9']*[0-9]+)((ull)|(ULL)|(llu)|(LLU)|(ul)|(UL)|(ll)|(LL)|[UuLl])?$"
)

cpp_digit_suffix_types = {
    "u": "unsigned int",
    "l": "long",
    "ul": "usngined long",
    "ll": "long long",
    "ull": "unsigned long long",
    "llu": "unsigned long long",
    "f": "float",
}
cpp_digit_suffix_types.update(
    {k.upper(): v for k, v in cpp_digit_suffix_types.items()}
)


@dataclass()
class CppDigit:
    value: int
    literal: str
    type: str


def _try_parse_cpp_digit_literal(literal: str):
    m = cpp_digit_re.match(literal)
    if m:
        digit = m.group(1)
        suffix = m.group(2)
        val = ast.literal_eval(digit.replace("'", ""))
        t = "int"
        if suffix:
            t = cpp_digit_suffix_types[suffix]
        return CppDigit(
            type=t, value=val, literal=literal
        )
    return None
