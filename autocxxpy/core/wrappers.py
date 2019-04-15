from abc import ABC, abstractmethod
from dataclasses import dataclass

from autocxxpy.type_manager import TypeManager, is_integer_type, is_string_type, \
    is_string_array_type
from autocxxpy.core.types.cxx_types import function_pointer_type_info, is_function_pointer_type, \
    is_reference_type, pointer_base, is_const_type, \
    is_pointer_type
from autocxxpy.core.types.generator_types import GeneratorFunction, GeneratorVariable


@dataclass()
class WrapperInfo:
    wrapper: "BaseFunctionWrapper"
    index: int


class BaseFunctionWrapper(ABC):
    name = "default_function_wrapper"
    compatible_wrapper_classes = []

    def __init__(self, type_manager: TypeManager):
        self.type_manager = type_manager

    @abstractmethod
    def match(self, f: GeneratorFunction, i: int, a: GeneratorVariable):
        """if matched, return the index of argument matched"""
        pass

    def wrap(self, f: GeneratorFunction, index: int):
        return f

    def is_arg_wrapped(self, f: GeneratorFunction, index: int):
        return index in {wi.index for wi in f.wrappers}  # todo: optimize speed

    def is_compatible_with_wrapped_arg(self, f: GeneratorFunction, index: int):
        if not self.compatible_wrapper_classes:
            return False
        wrapper =  [wi.wrapper for wi in f.wrappers if wi.index == index][0]
        return wrapper.__class__ in self.compatible_wrapper_classes

    def can_wrap_arg(self, f: GeneratorFunction, index: int):
        if not self.is_arg_wrapped(f, index):
            return True
        return self.is_compatible_with_wrapped_arg(f, index)


class CFunctionCallbackWrapper(BaseFunctionWrapper):
    name = "c_function_callback_transform"

    def match(self, f: GeneratorFunction, i: int, a: GeneratorVariable):
        length = len(f.args)
        if i + 1 < length:
            t = self.type_manager.resolve_to_basic_type(a.type)
            if is_function_pointer_type(t):
                fi = function_pointer_type_info(t)
                callback_last_param_type = fi.args[-1].type
                callback_last_param_type = self.type_manager.resolve_to_basic_type(callback_last_param_type)
                if callback_last_param_type == "void *":
                    next_param_type = f.args[i + 1].type
                    next_param_type = self.type_manager.resolve_to_basic_type(next_param_type)
                    if next_param_type == "void *":
                        return True

    def wrap(self, f: GeneratorFunction, index: int):
        args = f.args
        args[index].type = "std::vector<std::string>"
        f.args = args[:index + 1] + args[index + 2:]
        return f


class StringArrayWrapper(BaseFunctionWrapper):
    name = "string_array_transform"

    def match(self, f: GeneratorFunction, i: int, a: GeneratorVariable):
        length = len(f.args)
        if i+1 < length:
            if is_string_array_type(self.type_manager.resolve_to_basic_type(a.type)):
                a2 = f.args[i + 1]
                if is_integer_type(self.type_manager.resolve_to_basic_type(a2.type)):
                    return True
        return False

    def wrap(self, f: GeneratorFunction, index: int):
        args = f.args
        args[index].type = "std::vector<std::string>"
        f.args = args[:index + 1] + args[index + 2:]
        return f


class InoutArgumentWrapper(BaseFunctionWrapper):
    name = "inout_argument_transform"

    def match(self, f: GeneratorFunction, i: int, a: GeneratorVariable):
        if is_reference_type(a.type):
            if not is_const_type(a.type):
                return True
        t = self.type_manager.resolve_to_basic_type(a.type)
        if is_string_type(t):
            return False  # in most of the case char * is a input string

        if is_pointer_type(t):
            base = pointer_base(t)
            if is_integer_type(base):
                return True
            if is_string_type(base):
                return True

    def wrap(self, f: GeneratorFunction, index: int):
        # todo: fix output type(hint)
        return f


class OutputArgumentWrapper(BaseFunctionWrapper):
    name = "output_argument_transform"

    def match(self, f: GeneratorFunction, i: int, a: GeneratorVariable):
        if is_reference_type(a.type):
            if not is_const_type(a.type):
                return True
        t = self.type_manager.resolve_to_basic_type(a.type)
        if is_string_type(t):
            return False  # in most of the case char * is a input string

        if is_pointer_type(t):
            base = pointer_base(t)
            if is_integer_type(base):
                return True
            if is_string_type(base):
                return True

    def wrap(self, f: GeneratorFunction, index: int):
        args = f.args
        f.args = args[:index] + args[index + 1:]
        # todo: fix output type(hint)
        return f
