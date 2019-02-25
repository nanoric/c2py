# encoding: utf-8
import re

from .cxxparser import Function, Variable

base_types = {
    "char8_t",
    "char16_t",
    "char32_t",
    "wchar_t",
    "char",
    "short",
    "int",
    "long",
    "long long" "unsigned char",
    "unsigned short",
    "unsigned int",
    "unsigned long",
    "unsigned long long",
    "float",
    "double",
}


def is_array_type(t: str):
    return "[" in t


def array_base(t: str):
    """
    :raise ValueError if t is not a array type
    """
    t = t[: t.index("[")]
    while t.endswith(' '):
        t = t[:-1]
    return t


def is_pointer_type(t: str):
    """
    :param t:
    :return:
    :note function_type is also pointer type
    :sa is_function_type
    """
    return "*" in t


_REMOVE_POINTER_RE = re.compile("[ \t]*\\*[ \t]*")
_FUNCTION_POINTER_RE = re.compile("(\\w+) +\\((\\w*)\\*(\\w*)\\)\\((.*)\\)")


def strip(s: str):
    while s.startswith(' '):
        s = s[1:]
    while s.endswith(' '):
        s = s[:-1]
    return s


def is_function_type(t: str):
    # int32 (__cdecl*name)(OesApiSessionInfoT *, SMsgHeadT *, void *, OesQryCursorT *, void *)
    return _FUNCTION_POINTER_RE.match(t)


def function_type_info(t: str) -> Function:
    m = _FUNCTION_POINTER_RE.match(t)
    if m:
        ret_type = m.group(1)
        calling_convention = m.group(2)
        args_str = m.group(4)

        func = Function(
            name=m.group(3),
            ret_type=ret_type,
            calling_convention=calling_convention if calling_convention else None
        )
        func.args = [
            Variable(name='', type=strip(arg), parent=func)
            for arg in args_str.split(',')
        ]
        return func


def pointer_base(t: str):
    return _REMOVE_POINTER_RE.sub("", t)


def is_reference_type(t: str):
    return "&" in t


def remove_cvref(t: str):
    return (
        t.replace("const ", "")
            .replace("volatile ", "")
            .replace("&", "")
            .strip()
    )
