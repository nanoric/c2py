# encoding: utf-8

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from autocxxpy.types.generator_types import GeneratorClass, GeneratorEnum, GeneratorFunction, \
    GeneratorMethod, GeneratorNamespace, GeneratorVariable, to_generator_type
from autocxxpy.parser.cxxparser import CXXFileParser, CXXParseResult
from autocxxpy.types.parser_types import (Class, Enum, Function,
                                          Method, Namespace, Variable)
from autocxxpy.types.cxx_types import array_base, is_array_type, is_function_pointer_type, \
    is_pointer_type, \
    pointer_base
from autocxxpy.parser.utils import _try_parse_cpp_digit_literal, CppDigit
from autocxxpy.type_manager import TypeManager

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


def default_caster_filter(c: GeneratorClass):
    return True


def default_caster_name_for_class(c: GeneratorClass):
    return 'to' + c.name


@dataclass
class CasterOptions:
    enable: bool = True
    caster_filter: Callable[[GeneratorClass], bool] = field(
        default=default_caster_filter)
    caster_name_factory: Callable[[GeneratorClass], str] = field(
        default=default_caster_name_for_class)
    caster_name = 'cast'  # name


@dataclass
class PreProcessorOptions:
    parse_result: CXXParseResult
    remove_underline_prefix_for_typedefs: bool = True
    treat_const_macros_as_variable: bool = True
    ignore_global_variables_starts_with_underline: bool = True
    caster_options: CasterOptions = CasterOptions


@dataclass
class PreProcessorResult(GeneratorNamespace):
    const_macros: Dict[str, CppDigit] = field(default_factory=dict)
    type_alias: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    unsupported_functions: Dict[str, List[GeneratorFunction]] = field(
        default_factory=lambda: defaultdict(list))

    objects: Dict[str, Any] = field(default_factory=dict)
    parser_result: CXXParseResult = None


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

        self.typedef_reverse: Dict[str, Set[str]] = defaultdict(set)

        self.easy_names: Dict[str, str] = {}
        self.type_alias: Dict[str, Set[str]] = defaultdict(set)
        self.dict_classes = set()

        self.type_manager = TypeManager()
        self.type_manager.typedefs = self.options.parse_result.typedefs

    def process(self) -> PreProcessorResult:
        result = PreProcessorResult()
        options = self.options

        to_generator_type(options.parse_result.objects, None, result.objects)

        # typedefs
        self.process_typedefs()
        result.typedefs = self.parser_result.typedefs
        result.type_alias = self.type_alias

        # classes
        result.classes = self._process_classes(self.parser_result.classes)

        # namespaces
        result.namespaces = {
            name: GeneratorNamespace(**ns.__dict__)
            for name, ns in self.parser_result.namespaces.items()
        }

        # functions
        self._process_functions(result)

        # constant macros
        result.const_macros = self._process_constant_macros()

        # variables
        result.variables = {
            name: GeneratorVariable(**ov.__dict__)
            for name, ov in self.parser_result.variables.items()
        }

        # wrappers: c_func_pointer, string_array
        self._process_builtin_wrappers(result)
        result.enums = self._process_enums()

        # seeks unsupported functions
        for f in result.objects:
            if isinstance(f, GeneratorFunction):
                if not self._function_supported(f):
                    result.unsupported_functions[f.full_name].append(f)

        # post process
        if options.treat_const_macros_as_variable:
            for name, v in result.const_macros.items():
                var = GeneratorVariable(
                    name=name,
                    parent=None,
                    type=v.type,
                    const=True,
                    static=True,
                    value=v.value,
                    literal=v.literal,
                )
                result.variables[var.name] = var

        if options.ignore_global_variables_starts_with_underline:
            result.variables = {
                k: v for k, v in result.variables.items() if not k.startswith("_")
            }

        result.parser_result = self.parser_result
        return result

    def _is_type_supported(self, t: str):
        t = self.type_manager.resolve_to_basic_type(t)
        if is_pointer_type(t):
            pb = pointer_base(t)
            if is_pointer_type(pb):
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

    def process_typedefs(self):
        self.type_alias[''] = set()
        for name in self.parser_result.classes:
            self.easy_names[name] = name

        for name, tp in self.parser_result.typedefs.items():
            target = tp.target
            self.typedef_reverse[target].add(name)
            self.type_alias[target].add(name)
            self.type_alias[name].add(target)
            self.easy_names[name] = name
            self.easy_names[target] = name

        for name, alias in self.type_alias.items():
            n = name
            while n.startswith('_'):
                n = n[1:]
            if n in alias:
                self.easy_names[name] = n
            elif n + 'T' in alias:
                self.easy_names[name] = n + 'T'
            elif n + '_t' in alias:
                self.easy_names[name] = n + '_t'

    def _process_enums(self):
        enums: Dict[str, Enum] = {}
        for oe in self.parser_result.enums.values():
            e = GeneratorEnum(**oe.__dict__, alias=self._alias(oe))
            e.values = {
                name: GeneratorVariable(**v.__dict__)
                for name, v in oe.values.items()
            }

            self.convert_easy_name(e)
            for v in e.values.values():
                v.type = e.name
            enums[e.name] = e
        return enums

    def _process_classes(self, ocs: Dict):
        classes: Dict[str, GeneratorClass] = {}
        for oc in ocs.values():
            c = self._process_class(oc)
            classes[c.name] = c

        return classes

    def _alias(self, m):
        alias = m.name
        try:
            alias = self.easy_names[alias]
        except KeyError:
            pass
        if self.options.remove_underline_prefix_for_typedefs:
            while alias.startswith('_'):
                alias = alias[1:]
        return alias

    def _process_function(self, of: Function):
        f = GeneratorFunction(**of.__dict__, alias=self._alias(of))
        try:
            f.ret_type = self.easy_names[f.ret_type]
        except KeyError:
            pass
        return f

    def _process_functions(self, result):
        for name, ms in self.parser_result.functions.items():
            new_ms = [self._process_function(m) for m in ms]
            result.functions[name] = new_ms

    def _process_method(self, of: Function):
        f = GeneratorMethod(**of.__dict__, alias=self._alias(of))
        f.args = [GeneratorVariable(**{**ov.__dict__, "alias": ov.name}) for ov in f.args]
        try:
            f.ret_type = self.easy_names[f.ret_type]
        except KeyError:
            pass
        return f

    def _process_class(self, oc):
        c = GeneratorClass(**oc.__dict__)
        c.functions = {
            # name: [GeneratorMethod(**m.__dict__, alias=self._alias(m)) for m in ms]
            name: [self._process_method(m) for m in ms]
            for name, ms in oc.functions.items()
        }
        c.classes = self._process_classes(oc.classes)
        self.convert_easy_name(c)
        if c.is_polymorphic:
            c.force_to_dict = True
        for ms in c.functions.values():

            # check overload
            if len(ms) >= 2:
                for m in ms:
                    m.has_overload = True

            # check pure virtual
            for m in ms:
                if m.is_pure_virtual:
                    c.is_pure_virtual = True
        c.variables = {
            ov.name: GeneratorVariable(**ov.__dict__)
            for ov in c.variables.values()
        }

        return c

    def convert_easy_name(self, v: Any):
        if v.name in self.easy_names:
            v.name = self.easy_names[v.name]
        return v

    def _process_constant_macros(self):
        macros = {}
        for name, definition in self.parser_result.macros.items():
            value = PreProcessor._try_convert_to_constant(definition)
            if value is not None:
                value.name = name
                value.alias = name
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
