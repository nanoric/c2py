from typing import Dict

from autocxxpy.types.generator_types import GeneratorTypedef
from autocxxpy.types.cxx_types import (CXX_BASIC_TYPES, array_base, array_count_str, is_array_type,
                                       is_normal_pointer, pointer_base, remove_cvref)


class TypeManager:

    def __init__(self):
        self.typedefs: Dict[str, GeneratorTypedef] = {}

    def resolve_to_basic_type(self, t: str):
        t = remove_cvref(t)
        if is_normal_pointer(t):
            return self.resolve_to_basic_type(pointer_base(t)) + " *"
        if is_array_type(t):
            base = self.resolve_to_basic_type(array_base(t))
            return f'{base} [{array_count_str(t)}]'
        try:
            return self.typedefs[t].target
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
