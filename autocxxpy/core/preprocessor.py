# encoding: utf-8

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from autocxxpy.core.cxxparser import CXXFileParser, CXXParseResult
from autocxxpy.core.utils import CppDigit, _try_parse_cpp_digit_literal
from autocxxpy.objects_manager import ObjectManager
from autocxxpy.os.env import DEFAULT_INCLUDE_PATHS
from autocxxpy.type_manager import TypeManager
from autocxxpy.types.cxx_types import array_base, is_array_type, is_function_pointer_type, \
    is_pointer_type, \
    pointer_base
from autocxxpy.types.generator_types import AnyGeneratorSymbol, CallingType, GeneratorClass, \
    GeneratorEnum, GeneratorFunction, GeneratorMethod, GeneratorNamespace, GeneratorSymbol, \
    GeneratorVariable, to_generator_type
from autocxxpy.types.parser_types import (Class, Enum, Function, Method, Namespace, Symbol,
                                          Variable)


def is_built_in_symbol(f: Symbol):
    return f.location is None


INTERNAL_PATH_FLAG = {
    "Microsoft Visual Studio",
    "Windows Kits",
    "/usr"
}


def is_internal_symbol(symbol: Symbol):
    file_path = symbol.location.file
    for path in DEFAULT_INCLUDE_PATHS:
        if file_path.startswith(path):
            return True
    for flag in INTERNAL_PATH_FLAG:
        if flag in file_path:
            return True
    return False


string_array_bases = {
    'char *', 'const char *',
}

string_array_size_types = {
    'int',
}


def is_string_array_type(t: str):
    if is_array_type(t):
        base = array_base(t)
    elif is_pointer_type(t):
        base = pointer_base(t)
    else:
        return False
    return base in string_array_bases


def is_string_array_size_type(t: str):
    return t in string_array_size_types


@dataclass()
class PreProcessorOptions:
    parse_result: CXXParseResult
    treat_const_macros_as_variable: bool = True
    ignore_global_variables_starts_with_underline: bool = True
    ignore_unsupported_functions: bool = True


@dataclass()
class PreProcessorResult:
    g: GeneratorNamespace  # global namespace, cpp type tree starts from here
    const_macros: Dict[str, CppDigit] = field(default_factory=dict)
    type_alias: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    unsupported_functions: Dict[str, List[GeneratorFunction]] = field(
        default_factory=lambda: defaultdict(list))

    objects: ObjectManager = field(default_factory=dict)
    parser_result: CXXParseResult = None

    def print_unsupported_functions(self):
        print("unsupported functions:")
        for ms in self.unsupported_functions.values():
            for m in ms:
                print(m.signature)


class PreProcessor:
    type_map = {
        Variable: GeneratorVariable,
        Function: GeneratorFunction,
        Method: GeneratorMethod,
        Class: GeneratorClass,
        Namespace: GeneratorNamespace,
        Enum: GeneratorEnum,
    }

    def __init__(self, options: PreProcessorOptions):
        self.options = options
        self.parser_result = options.parse_result

        # noinspection PyTypeChecker
        self.type_manager: TypeManager = None

    def process(self) -> PreProcessorResult:
        options = self.options
        objects = ObjectManager()
        result = PreProcessorResult(to_generator_type(self.parser_result.g, None, objects))
        result.objects = objects
        self.type_manager = TypeManager(result.g)

        # classes
        self._process_namespace(result.g)

        # constant macros
        result.const_macros = self._process_constant_macros()

        # optional conversion process:
        # const macros -> variables
        if options.treat_const_macros_as_variable:
            for name, v in result.const_macros.items():
                var = GeneratorVariable(
                    name=name,
                    generate=v.generate,
                    objects=v.objects,
                    parent=None,
                    type=v.type,
                    const=True,
                    static=True,
                    value=v.value,
                    literal=v.literal,
                )
                result.g.variables[var.name] = var

        # ignore global variables starts with _
        if options.ignore_global_variables_starts_with_underline:
            result.g.variables = {
                k: v for k, v in result.g.variables.items() if not k.startswith("_")
            }

        self._process_functions_with_virtual_arguments_(result.objects)

        # wrappers: c_func_pointer, string_array
        self._process_builtin_wrappers(result.g)

        # seeks unsupported functions
        for f in result.objects.values():
            if isinstance(f, GeneratorFunction):
                if not self._function_supported(f):
                    result.unsupported_functions[f.full_name].append(f)
                    if self.options.ignore_unsupported_functions:
                        f.generate = False

        result.parser_result = self.parser_result
        return result

    def _process_functions_with_virtual_arguments_(self, objects: ObjectManager):
        """
        default implementation of async call will copy any pointer.
        But it is impossible to copy a polymorphic(has virtual method) class
        """

        def is_virtual_type(obj: GeneratorVariable):
            t = self.type_manager.remove_decorations(obj.type)
            try:
                obj = objects.resolve_all_typedef(t)
                if obj:
                    return obj.is_polymorphic
            except KeyError:
                pass
            return False

        for f in objects.values():
            if isinstance(f, GeneratorFunction):
                if any(map(is_virtual_type, f.args)):
                    f.calling_type = CallingType.Sync

    def _process_namespace(self, ns: GeneratorNamespace):
        # remove internal and built-in classes, enums, functions
        ns.classes = self._filter_dict(ns.classes)
        for c in ns.classes.values():
            self._process_class(c)
        ns.namespaces = self._filter_dict(ns.namespaces)
        for n in ns.namespaces.values():
            self._process_namespace(n)
        ns.variables = self._filter_dict(ns.variables)
        ns.enums = self._filter_dict(ns.enums)
        ns.functions = self._filter_dictlist(ns.functions)
        for ms in ns.functions.values():
            for m in ms:
                self._process_function(m)
        ns.typedefs = self._filter_dict(ns.typedefs)

    def _process_class(self, c: GeneratorClass):
        for ms in c.functions.values():
            # check overload
            if len(ms) >= 2:
                for m in ms:
                    m.has_overload = True
            # check pure virtual
            for m in ms:
                if m.is_pure_virtual:
                    c.is_pure_virtual = True

    def _process_function(self, f):
        assert type(f) in [GeneratorMethod, GeneratorFunction]
        if isinstance(f, GeneratorMethod):
            return self._process_method(f)
        return self._process_global_function(f)

    def _process_global_function(self, f: GeneratorFunction):
        pass

    def _process_method(self, f: GeneratorMethod):
        pass

    def _filter_dict(self, cs: Dict[str, GeneratorSymbol]) -> Dict[str, AnyGeneratorSymbol]:
        for s in cs.values():
            s.generate = self._should_output_symbol(s)
        return cs

    def _filter_list(self, cs: List[GeneratorSymbol]) -> List[AnyGeneratorSymbol]:
        for s in cs:
            s.generate = self._should_output_symbol(s)
        return cs

    def _filter_dictlist(self, fs: Dict[str, List[GeneratorSymbol]]) -> Dict[
        str, List[AnyGeneratorSymbol]]:
        for ms in fs.values():
            for m in ms:
                m.generate = self._should_output_symbol(m)
        return fs

    def _is_type_supported(self, t: str):
        t = self.type_manager.resolve_to_basic_type(t)
        if is_pointer_type(t):
            pb = pointer_base(t)
            if is_pointer_type(pb):
                return False  # level 2+ pointers
            if is_array_type(pb):
                return False
        return True

    def _function_supported(self, f: GeneratorFunction):
        for arg in f.args:
            t = arg.type
            if not self._is_type_supported(t):
                return False
        return True

    def _process_builtin_wrappers(self, result):
        # c function pointer wrapper
        self._wrap_c_function_pointers_for_namespace(result)
        for c in result.classes.values():
            self._wrap_c_function_pointers_for_namespace(c)

        # string_array wrapper
        self._wrap_string_array_for_namespace(result)
        for c in result.classes.values():
            self._wrap_string_array_for_namespace(c)

    def _wrap_string_array_for_namespace(self, n: Namespace):
        for ms in n.functions.values():
            for m in ms:
                self._wrap_string_array(m)
        for c in n.classes.values():
            self._wrap_string_array_for_namespace(c)

    def _wrap_string_array(self, m: Function):
        nargs = len(m.args)
        for i, a in enumerate(m.args):
            if (
                is_string_array_type(self.type_manager.resolve_to_basic_type(a.type))
                and i + 1 < nargs
                and is_string_array_size_type(
                self.type_manager.resolve_to_basic_type(m.args[i + 1].type))
            ):
                args = m.args

                # remove size argument
                m.args = args[:i + 1] + args[i + 2:]

                # convert type of this into normal array:
                # ->don't need to do anything!
                pass

    def _wrap_c_function_pointers_for_namespace(self, n: Namespace):
        for ms in n.functions.values():
            for m in ms:
                self._wrap_c_function_pointers(m)
        for c in n.classes.values():
            self._wrap_c_function_pointers_for_namespace(c)

    def _wrap_c_function_pointers(self, m: Function):
        nargs = len(m.args)
        for i, a in enumerate(m.args):
            if (
                # todo: is_function_type is not strict enough:
                # the logic here not the same as the cpp side.
                # last void * is not necessary here, but necessary in cpp side
                is_function_pointer_type(self.type_manager.resolve_to_basic_type(a.type))
                and i + 1 < nargs
                and self.type_manager.resolve_to_basic_type(m.args[i + 1].type) == 'void *'
            ):
                args = m.args

                # remove user supplied argument
                m.args = args[:i + 1] + args[i + 2:]

                # remove user supplied argument is function signature
                t = m.args[i].type
                m.args[i].type = t.replace(", void *)", ")")

    def _process_constant_macros(self):
        macros = {}
        for name, m in self.parser_result.macros.items():
            definition = m.definition
            value = PreProcessor._try_convert_to_constant(definition)
            if value is not None:
                value.name = name
                value.alias = name
                value.generate = self._should_output_symbol(m)
                macros[name] = value
        return macros

    @staticmethod
    def _try_convert_to_constant(definition: str) -> Optional[GeneratorVariable]:
        definition = definition.strip()
        try:
            if definition:
                var = _try_parse_cpp_digit_literal(definition)
                if var:
                    return var
                val = None
                if definition.startswith('"') and definition.endswith('"'):
                    val = ast.literal_eval(definition)
                    return GeneratorVariable(
                        name="",
                        type="const char *",
                        value=val,
                        literal=definition,
                    )
                if definition.startswith("'") and definition.endswith("'"):
                    val = CXXFileParser.character_literal_to_int(
                        definition[1:-1]
                    )
                    t = "unsigned int"
                    valid = True
                    if len(definition) >= 6:
                        t = "unsigned long long"
                        valid = False
                    return GeneratorVariable(
                        name="",
                        type=t,
                        value=val,
                        literal=definition,
                    )
        except SyntaxError:
            pass
        return None

    def _should_output_symbol(self, symbol: Symbol):
        return symbol.name and not is_built_in_symbol(symbol) and not is_internal_symbol(symbol)
