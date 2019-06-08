"""
type conversion between cpp, python and binding(currently pybind11)
"""
import logging
from typing import Any

from autocxxpy.core.types.cxx_types import (array_base, array_count_str, function_pointer_type_info,
                                            is_array_type, is_function_pointer_type,
                                            is_pointer_type, is_std_vector, pointer_base,
                                            remove_cvref, is_const_type)
from autocxxpy.core.types.generator_types import GeneratorClass, GeneratorEnum, GeneratorNamespace, \
    GeneratorTypedef
from autocxxpy.objects_manager import ObjectManager

logger = logging.getLogger(__file__)

ARRAY_BASES = {
    "char8_t": "str",
    "char16_t": "str",
    "char32_t": "str",
    "wchar_t": "str",
    "char": "str",
    "void": "Any",
}
STRING_BASE_TYPES = {
    "char *", "const char *",
    "std::string", "const std::string",
}
CPP_BASE_TYPE_TO_PYTHON = {
    "char8_t": "str",
    "char16_t": "str",
    "char32_t": "str",
    "wchar_t": "str",
    "char": "str",
    "signed char": "str",
    
    "short": "int",
    "int": "int",
    "long": "int",
    "long long": "int",
    "signed short": "int",
    "signed int": "int",
    "signed long": "int",
    "signed long long": "int",
    "unsigned char": "int",
    "unsigned short": "int",
    "unsigned int": "int",
    "unsigned long": "int",
    "unsigned long long": "int",
    "float": "float",
    "double": "float",
    "long double": "float",
    "bool": "bool",
    "char *": "str",
    "std::string": "str",  # if template can be resolved, maybe it is not a std::string?
    "void": "None",
}
PYTHON_TYPE_TO_PYBIND11 = {
    "int": "int_",
    "bool": "bool_",
    "float": "float_",
    "str": "str",
    "None": "none",
    int: "int_",
    float: "float_",
    str: "str",
    bool: "bool_",
    None: "none",
}

type_prefixes = {
    'struct ', 'enum', "union ", "class "
}


def python_type_to_pybind11(t: str):
    return PYTHON_TYPE_TO_PYBIND11[t]


def cpp_base_type_to_python(ot: str):
    return CPP_BASE_TYPE_TO_PYTHON[remove_cvref(ot)]


def cpp_base_type_to_pybind11(t: str):
    t = remove_cvref(t)
    return PYTHON_TYPE_TO_PYBIND11[cpp_base_type_to_python(t)]


def python_value_to_cpp_literal(val: Any):
    t = type(val)
    if t is str:
        return f'"({val})"'
    if t is int:
        return f"({val})"
    if t is float:
        return f"(double({val}))"


def is_integer_type(ot: str):
    t = remove_cvref(ot)
    try:
        return cpp_base_type_to_python(t) == 'int'
    except KeyError:
        return False


def is_string_type(ot: str):
    t = remove_cvref(ot)
    if is_array_type(t):
        b = array_base(t)
        return b in ARRAY_BASES and ARRAY_BASES[b] == 'str'  # special case: string array
    try:
        return t in STRING_BASE_TYPES
    except KeyError:
        return False


def is_string_array_type(ot: str):
    t = remove_cvref(ot)
    if is_array_type(t):
        base = array_base(t)
    elif is_pointer_type(t):
        base = pointer_base(t)
    else:
        return False
    return is_string_type(remove_cvref(base))


def is_tuple_type(ot: str):
    t = remove_cvref(ot)
    return t.startswith('std::tuple<')


def tuple_elements(t: str):
    elements_str = t[11:-1]
    return [i.strip() for i in elements_str.split(',')]


def tuple_length(t: str):
    return len(tuple_elements(t))


def tuple_type_add(t: str, e: str):
    return make_tuple_type(*tuple_elements(t), e)


def make_tuple_type(*args):
    return f'std::tuple<{",".join(args)}>'


class TypeManager:

    def __init__(self, g: GeneratorNamespace, objects: ObjectManager):
        self.g: GeneratorNamespace = g
        self.objects = objects

    def remove_decorations(self, ot: str):
        """
        remove pointers, array, cvref
        """
        t = remove_cvref(ot)
        if is_pointer_type(t):
            return self.remove_decorations(pointer_base(t))
        if is_array_type(t):
            return self.remove_decorations(array_base(t))
        return t

    def resolve_to_basic_type_remove_const(self, ot: str):
        t = remove_cvref(ot)
        if is_pointer_type(t):
            return self.resolve_to_basic_type_remove_const(pointer_base(t)) + " *"
        if is_array_type(t):
            base = self.resolve_to_basic_type_remove_const(array_base(t))
            if is_std_vector(t):
                return f'std::vector<{self.resolve_to_basic_type_remove_const(base)}>'
            return f'{base} [{array_count_str(t)}]'
        try:
            obj = self.objects[t]
            if isinstance(obj, GeneratorTypedef) and obj.full_name != obj.target:
                return self.resolve_to_basic_type_remove_const(obj.target)
        except KeyError:
            pass
        return t

    def is_pointer_type(self):
        pass

    def is_basic_type(self, t: str):
        t = self.resolve_to_basic_type_remove_const(t)

        if (
            is_array_type(t) and
            array_base(t) in CPP_BASE_TYPE_TO_PYTHON
        ):
            return True
        return False

    def cpp_type_to_pybind11(self, t: str):
        """
        :param t: full name of type
        :return: pybind11 type name, without namespace prefix
        """
        return python_type_to_pybind11(self.cpp_type_to_python(t))

    def _remove_variable_type_prefix(self, t: str):
        for p in type_prefixes:
            if t.startswith(p):
                return t[len(p):]
        return t

    def cpp_type_to_python(self, ot: str):
        """
        convert to basic type combination

        :param t: full name of type
        :return:
        """
        t = ot
        t = remove_cvref(t)
        t = self._remove_variable_type_prefix(t)
        try:
            return cpp_base_type_to_python(t)
        except KeyError:
            pass
        if is_function_pointer_type(t):
            func = function_pointer_type_info(t)
            args = ",".join([self.cpp_type_to_python(arg.type) for arg in func.args])
            return f'Callable[[{args}], {self.cpp_type_to_python(func.ret_type)}]'
        if is_pointer_type(t):
            cpp_base = self.resolve_to_basic_type_remove_const(pointer_base(t))
            if is_pointer_type(cpp_base) or is_array_type(cpp_base):
                return f'"level 2 pointer:{t}"'  # un-convertible: level 2 pointer
            if cpp_base in ARRAY_BASES:
                return ARRAY_BASES[cpp_base]
            return self.cpp_type_to_python(cpp_base)
        if is_array_type(t):
            b = array_base(t)
            if b in ARRAY_BASES:  # special case: string array
                return ARRAY_BASES[b]
            base = self.cpp_type_to_python(b)
            return f'List[{base}]'
        if is_tuple_type(t):
            es = tuple_elements(t)
            bases = [self.cpp_type_to_python(i) for i in es]
            bases_str = ",".join(bases)
            return f'Tuple[{bases_str}]'

        # check classes
        objects = self.objects
        if t in objects:
            o = objects[t]
            if isinstance(o, GeneratorClass) or isinstance(o, GeneratorEnum):
                return t.replace("::", ".").strip(" .")  # todo fix this
            if isinstance(o, GeneratorTypedef):
                return self.cpp_type_to_python(o.target)

        if t.startswith("(anonymous"):
            return f'"{t}"'

        # this means this is
        logger.warning("%s might be an internal symbol, failed to resolve to basic type", t)
        return t
