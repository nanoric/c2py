from typing import Dict, Any

from autocxxpy.types.generator_types import GeneratorNamespace
from autocxxpy.types.parser_types import Typedef
from autocxxpy.types.cxx_types import (CXX_BASIC_TYPES, array_base, array_count_str, is_array_type,
                                       is_normal_pointer, pointer_base, remove_cvref,
                                       is_function_pointer_type, function_pointer_type_info,
                                       is_pointer_type)
cpp_str_bases = {"char", "wchar_t", "char8_t", "char16_t", "char32_t"}
cpp_base_type_to_python_map = {
    "char8_t": "int",
    "char16_t": "int",
    "char32_t": "int",
    "wchar_t": "int",
    "char": "int",
    "short": "int",
    "int": "int",
    "long": "int",
    "long long": "int",
    "signed char": "int",
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
    "bool": "bool",
    "void": "Any",
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


def python_type_to_pybind11(t: str):
    return PYTHON_TYPE_TO_PYBIND11[t]


def cpp_base_type_to_python(ot: str):
    t = remove_cvref(ot)
    if is_pointer_type(t):
        if pointer_base(t) in cpp_str_bases:
            return "str"
    if is_array_type(t):
        if array_base(t) in cpp_str_bases:
            return "str"
    if t in cpp_base_type_to_python_map:
        return cpp_base_type_to_python_map[t]
    return None


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


class TypeManager:

    def __init__(self, g: GeneratorNamespace):
        self.g: GeneratorNamespace = g

    def resolve_to_basic_type(self, t: str):
        t = remove_cvref(t)
        if is_normal_pointer(t):
            return self.resolve_to_basic_type(pointer_base(t)) + " *"
        if is_array_type(t):
            base = self.resolve_to_basic_type(array_base(t))
            return f'{base} [{array_count_str(t)}]'
        try:
            return self.g.typedefs[t].target
        except KeyError:
            return t

    def is_pointer_type(self):
        pass

    def is_basic_type(self, t: str):
        t = self.resolve_to_basic_type(t)

        if (
            is_array_type(t) and
            array_base(t) in CXX_BASIC_TYPES
        ):
            return True
        return False

    def cpp_type_to_pybind11(self, t: str):
        """
        :param t: full name of type
        :return: pybind11 type name, without namespace prefix
        """
        return python_type_to_pybind11(self.cpp_type_to_python(t))

    def cpp_type_to_python(self, t: str):
        """
        :param t: full name of type
        :return:
        """
        t = remove_cvref(t)
        base_type = cpp_base_type_to_python(t)
        if base_type:
            return base_type
        if is_function_pointer_type(t):
            func = function_pointer_type_info(t)
            args = ",".join([self.cpp_type_to_python(arg.type) for arg in func.args])
            return f'Callable[[{args}], {self.cpp_type_to_python(func.ret_type)}]'
        if is_pointer_type(t):
            return self.cpp_type_to_python(pointer_base(t))
        if is_array_type(t):
            base = self.cpp_type_to_python(array_base(t))
            return f'Sequence[{base}]'

        # check classes
        if t in self.options.g.classes:
            return t

        # check enums
        if t in self.options.g.enums:
            return t

        if t in self.options.g.typedefs:
            return self.cpp_type_to_python(self.options.g.typedefs[t].target)

        return cpp_base_type_to_python(t)


