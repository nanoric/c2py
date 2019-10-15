# encoding: utf-8

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Set, Type

from c2py.core.core_types.cxx_types import array_base, is_array_type, is_pointer_type, \
    pointer_base
from c2py.core.core_types.generator_types import AnyGeneratorSymbol, CallingType, \
    GeneratorClass, GeneratorEnum, GeneratorFunction, GeneratorMethod, GeneratorNamespace, \
    GeneratorSymbol, GeneratorVariable, GeneratorVariableFromMacro, to_generator_type
from c2py.core.core_types.parser_types import (Class, Enum, Function, Method, Namespace,
                                                    Symbol,
                                                    Variable)
from c2py.core.cxxparser import CXXParseResult
from c2py.core.env import DEFAULT_INCLUDE_PATHS
from c2py.core.utils import _try_parse_cpp_char_literal, _try_parse_cpp_digit_literal, \
    _try_parse_cpp_string_literal, CppLiteral
from c2py.core.wrappers import BaseFunctionWrapper, CFunctionCallbackWrapper, \
    InoutArgumentWrapper, OutputArgumentWrapper, StringArrayWrapper, WrapperInfo
from c2py.objects_manager import ObjectManager
from c2py.type_manager import TypeManager


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


@dataclass()
class PreProcessorOptions:
    parse_result: CXXParseResult
    treat_const_macros_as_variable: bool = True
    ignore_global_variables_starts_with_underline: bool = True
    ignore_unsupported_functions: bool = True
    inout_arg_pattern: Optional[Pattern] = None
    output_arg_pattern: Optional[Pattern] = None
    # char_macro_to_int: bool = False


@dataclass()
class PreProcessorResult:
    g: GeneratorNamespace  # global namespace, cpp type tree starts from here
    const_macros: Dict[str, GeneratorVariable] = field(default_factory=dict)
    type_alias: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    unsupported_functions: Dict[str, List[GeneratorFunction]] = field(
        default_factory=lambda: defaultdict(list))

    objects: ObjectManager = field(default_factory=dict)
    parser_result: CXXParseResult = None

    def print_unsupported_functions(self):
        print(f"# of unsupported functions: {len(self.unsupported_functions)}")
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
        self.type_manager = TypeManager(result.g, objects)

        # classes
        self._process_namespace(result.g)

        # constant macros
        result.const_macros = self._process_constant_macros()

        # optional conversion process:
        # const macros -> variables
        if options.treat_const_macros_as_variable:
            for name, v in result.const_macros.items():
                var = GeneratorVariableFromMacro(
                    name=name,
                    generate=v.generate,
                    location=v.location,
                    parent=None,
                    type=v.type,
                    const=True,
                    static=True,
                    value=v.value,
                    literal=v.literal,
                )
                result.g.variables[var.name] = var
                result.objects[var.full_name] = var

        # ignore global variables starts with _
        if options.ignore_global_variables_starts_with_underline:
            result.g.variables = {
                k: v for k, v in result.g.variables.items() if not k.startswith("_")
            }

        self._process_functions(result.objects)

        # seeks unsupported functions
        for s in result.objects.values():
            if not self._should_output_symbol(s):
                s.generate = False
                continue

            if isinstance(s, GeneratorFunction):
                if not self._function_supported(s):
                    result.unsupported_functions[s.full_name].append(s)
                    if self.options.ignore_unsupported_functions:
                        s.generate = False

        result.parser_result = self.parser_result
        return result

    def _try_wrapper(self, f: GeneratorFunction, wrapper: BaseFunctionWrapper):
        for i, a in enumerate(f.args):
            if wrapper.can_wrap_arg(f, i):
                return WrapperInfo(wrapper=wrapper, index=i)

    def _apply_wrappers_one_round(self, of: GeneratorFunction, wrappers: List[BaseFunctionWrapper]):
        wrapped = False
        wf = of.resolve_wrappers()
        for w in wrappers:
            res = True
            while res:
                res = self._try_wrapper(wf, w)
                if res:
                    of.wrappers.append(res)
                    wf = of.resolve_wrappers()
                    wrapped = True
        return wrapped

    def _process_functions(self, objects: ObjectManager):
        wrapper_classes = [CFunctionCallbackWrapper, StringArrayWrapper, InoutArgumentWrapper]
        wrappers: List[BaseFunctionWrapper] = [i(self.type_manager) for i in wrapper_classes]

        # get all function from objects
        fs: List[GeneratorFunction] = []
        for f in objects.values():
            if isinstance(f, GeneratorFunction):
                fs.append(f)

        # apply user supplied wrappers first
        if self.options.output_arg_pattern:
            self._apply_user_wrapper_by_pattern(
                fs,
                self.options.output_arg_pattern,
                OutputArgumentWrapper)
        if self.options.inout_arg_pattern:
            self._apply_user_wrapper_by_pattern(
                fs,
                self.options.inout_arg_pattern,
                InoutArgumentWrapper)

        for of in fs:
            # keep apply wrapper until no wrapper can be applied
            wrapped = True
            while wrapped:
                wrapped = self._apply_wrappers_one_round(of, wrappers)

        self._process_functions_with_virtual_arguments_(objects)

    def _try_user_wrapper(self, wf: GeneratorFunction, regex: Pattern,
                          wrapper: BaseFunctionWrapper):
        for i, a in enumerate(wf.args):
            if regex.match(a.full_name):
                # if not wrapper.can_wrap_arg(wf, i):
                #     _ = wrapper.can_wrap_arg(wf, i)
                #     pass
                assert wrapper.can_wrap_arg(wf, i), \
                    f"Argument {a.full_name} matches {regex.pattern}, but not satisfy the requirements of {wrapper.__class__}"
                return WrapperInfo(wrapper=wrapper, index=i)

    def _apply_user_wrapper_by_pattern(self,
                                       fs: List[GeneratorFunction],
                                       regex: Pattern,
                                       wrapper_class: Type[BaseFunctionWrapper]):
        wrapper = wrapper_class(self.type_manager)
        for of in fs:
            wf = of.resolve_wrappers()
            res = True
            while res:
                res = self._try_user_wrapper(wf, regex, wrapper)
                if res:
                    of.wrappers.append(res)
                    wf = of.resolve_wrappers()

    def _process_functions_with_virtual_arguments_(self, objects: ObjectManager):
        """
        default implementation of async call will copy any pointer.
        But it is impossible to copy a polymorphic(has virtual method) class
        """

        def is_virtual_type(obj: GeneratorVariable):
            t = self.type_manager.remove_decorations(obj.type)
            try:
                obj = objects.resolve_all_typedef(t)
                if isinstance(obj, GeneratorClass):
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
            if len(ms) >= 2:
                for m in ms:
                    m.has_overload = True
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
        t = self.type_manager.resolve_to_basic_type_remove_const(t)
        if is_pointer_type(t):
            b = pointer_base(t)
            if is_pointer_type(b):
                return False  # level 2+ pointers
            if is_array_type(b):
                return False
        if is_array_type(t):
            b = array_base(t)
            if is_pointer_type(b):
                return False  # level 2+ pointers
            if is_array_type(b):
                return False
        return True

    def _function_supported(self, f: GeneratorFunction):
        for arg in f.resolve_wrappers().args:
            t = arg.type
            if not self._is_type_supported(t):
                return False
        return True

    def _process_constant_macros(self):
        macros = {}
        for name, m in self.parser_result.macros.items():
            definition = m.definition
            value = self._try_convert_macro_to_constant(definition)
            if value is not None:
                value.name = name
                value.alias = name
                value.location = m.location
                value.brief_comment = m.brief_comment
                value.generate = self._should_output_symbol(m)
                macros[name] = value
        return macros

    @staticmethod
    def _try_convert_macro_to_constant(definition: str) -> Optional[GeneratorVariable]:
        definition = definition.strip()
        if definition:
            parsers = (
                _try_parse_cpp_digit_literal,
                _try_parse_cpp_string_literal,
                _try_parse_cpp_char_literal,
            )

            for parser in parsers:
                var: CppLiteral = parser(definition)
                if var:
                    return GeneratorVariable(
                        name='',
                        type=var.cpp_type,
                        value=var.value,
                        literal=definition,
                    )
        return None

    @staticmethod
    def _should_output_symbol(symbol: Symbol):
        if hasattr(symbol, 'access'):
            if symbol.access != 'public':
                return False

        return (symbol.name
                and not is_built_in_symbol(symbol)
                and not is_internal_symbol(symbol)
                )
