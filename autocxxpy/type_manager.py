"""
type conversion between cpp, python and binding(currently pybind11)
"""
from typing import Dict, Any

from autocxxpy.types.generator_types import GeneratorNamespace, GeneratorTypedef, GeneratorClass, \
    GeneratorEnum
from autocxxpy.types.cxx_types import (array_base, array_count_str, is_array_type,
                                       is_pointer_type, pointer_base, remove_cvref,
                                       is_function_pointer_type, function_pointer_type_info,
                                       is_pointer_type)

CPP_BASE_TYPE_TO_PYTHON = {
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
    "char *": "str",
    "std::string": "str",  # if template can be resolved, maybe it is not a std::string?
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

type_prefixes = {
    'struct ', 'enum', "union ", "class "
}


def python_type_to_pybind11(t: str):
    return PYTHON_TYPE_TO_PYBIND11[t]


def cpp_base_type_to_python(ot: str):
    t = remove_cvref(ot)
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


def is_integer_type(t: str):
    try:
        return cpp_base_type_to_python(t) == 'int'
    except KeyError:
        return False


def is_string_type(t: str):
    try:
        return cpp_base_type_to_python(t) == 'str'
    except KeyError:
        return False


def is_string_array_type(t: str):
    if is_array_type(t):
        base = array_base(t)
    elif is_pointer_type(t):
        base = pointer_base(t)
    else:
        return False
    return is_string_type(remove_cvref(base))


class TypeManager:

    def __init__(self, g: GeneratorNamespace):
        self.g: GeneratorNamespace = g

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

    def resolve_to_basic_type(self, ot: str):
        t = remove_cvref(ot)
        if is_pointer_type(t):
            return self.resolve_to_basic_type(pointer_base(t)) + " *"
        if is_array_type(t):
            base = self.resolve_to_basic_type(array_base(t))
            return f'{base} [{array_count_str(t)}]'
        try:
            obj = self.g.objects[t]
            if isinstance(obj, GeneratorTypedef) and obj.full_name != obj.target:
                return self.resolve_to_basic_type(obj.target)
        except KeyError:
            pass
        return t

    def is_pointer_type(self):
        pass

    def is_basic_type(self, t: str):
        t = self.resolve_to_basic_type(t)

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

    def cpp_type_to_python(self, t: str):
        """
        :param t: full name of type
        :return:
        """
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
            return self.cpp_type_to_python(pointer_base(t))
        if is_array_type(t):
            base = self.cpp_type_to_python(array_base(t))
            return f'Sequence[{base}]'

        # check classes
        objects = self.g.objects
        if t in objects:
            o = objects[t]
            if isinstance(o, GeneratorClass) or isinstance(o, GeneratorEnum):
                return t
            if isinstance(o, GeneratorTypedef):
                return self.cpp_type_to_python(self.g.typedefs[t].target)

        return cpp_base_type_to_python(t)


