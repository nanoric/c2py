# encoding: utf-8
"""
type traits
"""
import functools
import re

from autocxxpy.core.types.parser_types import Function, Variable

_REMOVE_POINTER_RE = re.compile("[ \t]*\\*[ \t]*")
_FUNCTION_POINTER_RE = re.compile("(\\w+) +\\((\\w*)\\*(\\w*)\\)\\((.*)\\)")


@functools.lru_cache()
def is_const_type(t: str):
    if is_pointer_type(t):
        return t.endswith("const")
    return t.startswith('const ')


@functools.lru_cache()
def is_array_type(ot: str):
    t = remove_cvref(ot)
    if is_std_vector(t):
        return True
    return is_c_array_type(t)


@functools.lru_cache()
def is_c_array_type(ot: str):
    t = remove_cvref(ot)
    return t.endswith(']')


@functools.lru_cache()
def is_std_vector(t: str):
    return remove_cvref(t).startswith("std::vector<")


@functools.lru_cache()
def is_pointer_type(t: str):
    """
    check if t is a T *
    """
    return remove_cvref(t).endswith('*')


@functools.lru_cache()
def is_reference_type(t: str):
    return "&" in t


@functools.lru_cache()
def is_function_pointer_type(t: str):
    # int32 (__cdecl*name)(OesApiSessionInfoT *, SMsgHeadT *, void *, OesQryCursorT *, void *)
    return _FUNCTION_POINTER_RE.match(t)


@functools.lru_cache()
def pointer_base(ot: str):
    t = ot
    if t.endswith('const'):  # fixme: not only const?
        t = remove_const_volatile(ot)
        return 'const ' + t[:-1].strip()
    return t[:-1].strip()


@functools.lru_cache()
def reference_base(t: str):
    return remove_ref(t)


@functools.lru_cache()
def array_base(ot: str):
    """
    :raise ValueError if t is not a array type
    """
    t = remove_cvref(ot)
    if is_std_vector(t):
        t = t[12:-1]
    else:
        t = t[: t.rindex("[")]
    return t.strip()


@functools.lru_cache()
def array_count_str(ot: str):
    t = remove_cvref(ot)
    t = t[t.rindex("[") + 1:]
    t = t[:-1]
    return t


@functools.lru_cache()
def array_count(ot: str):
    """
    :return: array_count, 0 if no count in this type.
    """
    t = remove_cvref(ot)
    t = array_count_str(t)
    if t:
        return int(t)
    return 0


@functools.lru_cache()
def function_pointer_type_info(t: str) -> Function:
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
            Variable(name='', type=arg.strip(), parent=func)
            for arg in args_str.split(',')
        ]
        return func


@functools.lru_cache()
def remove_cvref(t: str):
    return remove_ref(remove_const_volatile(t))


@functools.lru_cache()
def remove_ref(t: str):
    if t.endswith('&'):
        return t[:-1].strip()
    return t


def remove_decorator(ot: str, decorator: str):
    t = ot
    length = len(decorator)
    if t.endswith(decorator):
        t = t[:-length]
    if t.startswith(decorator):
        t = t[length:]
    return t.strip()


@functools.lru_cache()
def remove_const_volatile(ot: str):
    t = ot
    while True:
        nt = t
        nt = remove_decorator(nt, 'const')
        nt = remove_decorator(nt, 'volatile')
        if nt == t:
            t = nt
            break
        t = nt

    return (
            t.replace("volatile ", "")
            .strip()
    )

