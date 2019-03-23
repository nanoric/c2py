# encoding: utf-8

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from autocxxpy.parser.cxxparser import CXXParseResult, CXXFileParser
from autocxxpy.parser.utils import _try_parse_cpp_digit_literal
from autocxxpy.parser.cxxparser_types import (Class, Enum, Function, LiteralVariable,
                        Method, Namespace, Variable)
from autocxxpy.parser.type import array_base, base_types, is_array_type, is_function_type, is_pointer_type, \
    pointer_base

string_array_bases = {
    'char *', 'const char *',
}

string_array_size_types = {
    'int',
}


def is_string_array(t: str):
    if is_array_type(t):
        base = array_base(t)
    elif is_pointer_type(t):
        base = pointer_base(t)
    else:
        return False
    return base in string_array_bases


def is_string_array_size_type(t: str):
    return t in string_array_size_types


@dataclass
class GeneratorVariable(Variable):
    alias: str = ""

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name


@dataclass
class GeneratorLiteralVariable(LiteralVariable, GeneratorVariable):
    alias: str = ""

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name


@dataclass
class GeneratorNamespace(Namespace):
    parent: "GeneratorNamespace" = None

    alias: str = ""
    enums: Dict[str, "GeneratorEnum"] = field(default_factory=dict)
    typedefs: Dict[str, str] = field(default_factory=dict)
    classes: Dict[str, "GeneratorClass"] = field(default_factory=dict)
    variables: Dict[str, "GeneratorVariable"] = field(default_factory=dict)
    functions: Dict[str, List["GeneratorFunction"]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    namespaces: Dict[str, List["GeneratorNamespace"]] = field(default_factory=(lambda: defaultdict(list)))

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name
        self.classes = {
            name: GeneratorClass(**oc.__dict__)
            for name, oc in self.classes.items()
        }
        self.enums = {
            name: GeneratorEnum(**oe.__dict__)
            for name, oe in self.enums.items()
        }
        self.variables = {
            name: self.to_generator_variable(ov)
            for name, ov in self.variables.items()
        }
        self.functions = {
            name: [
                GeneratorFunction(**m.__dict__) if type(m) is Function or type(
                    m) is GeneratorFunction
                else GeneratorMethod(**m.__dict__)
                for m in ms
            ]
            for name, ms in self.functions.items()
        }
        self.namespaces = {
            name: GeneratorNamespace(**n.__dict__)
            for name, n in self.namespaces.items()
        }

    @staticmethod
    def to_generator_variable(ov):
        kwargs: dict = {**ov.__dict__}
        if 'literal' in kwargs:
            return GeneratorLiteralVariable(**kwargs)
        return GeneratorVariable(**kwargs)


@dataclass
class GeneratorFunction(Function, GeneratorNamespace):
    ret_type: str = ''

    args: List[GeneratorVariable] = field(default_factory=list)

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name
        self.args = [
            GeneratorVariable(**oc.__dict__)
            for oc in self.args
        ]


@dataclass
class GeneratorEnum(GeneratorNamespace, Enum):
    type: str = ''

    values: Dict[str, GeneratorVariable] = field(default_factory=dict)

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name
        self.values = {
            name: GeneratorVariable(**oc.__dict__)
            for name, oc in self.values.items()
        }


@dataclass
class GeneratorMethod(Method, GeneratorFunction, GeneratorNamespace):
    ret_type: str = ''
    parent: Class = None
    has_overload: bool = False


@dataclass
class GeneratorClass(Class, GeneratorNamespace):
    functions: Dict[str, List[GeneratorMethod]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    force_to_dict: bool = False  # if need_wrap is true, wrap this to dict(deprecated)
    # generator will not assign python constructor for pure virtual
    is_pure_virtual: bool = False


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

    # not used:
    find_dict_class: bool = False


@dataclass
class PreProcessorResult(GeneratorNamespace):
    dict_classes: Set[str] = field(default_factory=set)
    const_macros: Dict[str, GeneratorLiteralVariable] = field(default_factory=dict)
    caster_class: GeneratorClass = None
    type_alias: Dict[str, Set[str]] = field(default_factory=lambda : defaultdict(list))

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

    def process(self) -> PreProcessorResult:
        result = PreProcessorResult()
        options = self.options

        # all pod struct to dict
        # todo: generator doesn't support dict class currently
        if options.find_dict_class:
            self.dict_classes = self._find_dict_classes()
            result.dict_classes = self.dict_classes

        # typedefs
        self.process_typedefs()
        result.typedefs = self.parser_result.typedefs
        result.type_alias = self.type_alias

        # functions
        self._process_functions(result)

        # classes
        result.classes = self._process_classes(self.parser_result.classes)

        # constant macros
        result.const_macros = self._process_constant_macros()

        # variables
        result.variables = {
            name: GeneratorVariable(**ov.__dict__)
            for name, ov in self.parser_result.variables.items()
        }

        self._process_builtin_wrappers(result)
        result.enums = self._process_enums()

        # caster
        if options.caster_options.enable:
            caster: GeneratorClass = self._process_caster(result.classes)
            result.caster_class = caster

        # post process
        if options.treat_const_macros_as_variable:
            result.variables.update(result.const_macros)

        if options.ignore_global_variables_starts_with_underline:
            result.variables = {
                k: v for k, v in result.variables.items() if not k.startswith("_")
            }

        result.parser_result = self.parser_result
        return result

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
        for i, a in enumerate(m.args):
            if (
                is_string_array(self._to_basic_type_combination(a.type)) and
                is_string_array_size_type(self._to_basic_type_combination(m.args[i + 1].type))
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
        for i, a in enumerate(m.args):
            if (
                # todo: is_function_type is not strict enough:
                # the logic here not the same as the cpp side.
                # last void * is not necessary here, but necessary in cpp side
                is_function_type(self._to_basic_type_combination(a.type)) and
                self._to_basic_type_combination(m.args[i + 1].type) == 'void *'
            ):
                args = m.args

                # remove user supplied argument
                m.args = args[:i + 1] + args[i + 2:]

                # remove user supplied argument is function signature
                t = m.args[i].type
                m.args[i].type = t.replace(", void *)", ")")

    def _generator_caster_function(self, c: GeneratorClass):
        if self.options.caster_options.caster_filter(c):
            n = self.options.caster_options.caster_name_factory(c)
            if n:
                func = GeneratorMethod(
                    name=n,
                    ret_type=c.name,
                    parent=c,

                )
                func.args.append(GeneratorVariable(name="v", type="void *", parent=func))
                func.ret_type = self.easy_names[func.ret_type]
                return func

    def _process_caster(self, classes: Dict[str, GeneratorClass]):
        option = self.options.caster_options
        caster_class = GeneratorClass(
            name=option.caster_name,
        )
        caster_functions = caster_class.functions
        # typedefs
        for oc in classes.values():
            c = GeneratorClass(**oc.__dict__)
            func = self._generator_caster_function(c)
            if func:
                caster_functions[func.name] = [func]

            for name in self.type_alias[c.name]:
                c.name = name
                func = self._generator_caster_function(c)
                if func:
                    caster_functions[func.name] = [func]
        return caster_class

    def process_typedefs(self):
        self.type_alias[''] = set()
        for name in self.parser_result.classes:
            self.easy_names[name] = name

        for name, target in self.parser_result.typedefs.items():
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
        f.args = [GeneratorVariable(**{**ov.__dict__, "alias":ov.name}) for ov in f.args]
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

    def _find_dict_classes(self):
        dict_classes = set()
        for c in self.parser_result.classes.values():
            if self._can_convert_to_dict(c):
                dict_classes.add(c.name)
        return dict_classes

    def _to_basic_type_combination(self, t: str):
        try:
            return self._to_basic_type_combination(
                self.parser_result.typedefs[t]
            )
        except KeyError:
            return t

    def _is_basic_type(self, t: str):
        basic_combination = self._to_basic_type_combination(t)

        # just a basic type, such as int, char, short, double etc.
        if basic_combination in base_types:
            return True

        # array of basic type, such as int[], char[]
        if (
            is_array_type(basic_combination) and
            array_base(basic_combination) in base_types
        ):
            return True

        return False

    def _can_convert_to_dict(self, c: Class):
        # first: no functions
        if c.functions:
            return False

        # second: all variables are basic
        for v in c.variables.values():
            if not self._is_basic_type(v.type):
                return False

        return True

    @staticmethod
    def _try_convert_to_constant(definition: str) -> Optional[GeneratorLiteralVariable]:
        definition = definition.strip()
        try:
            if definition:
                var = _try_parse_cpp_digit_literal(definition)
                if var:
                    return var
                val = None
                if definition.startswith('"') and definition.endswith('"'):
                    val = ast.literal_eval(definition)
                    return GeneratorLiteralVariable(
                        name="",
                        type="const char *",
                        default=val,
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
                    return GeneratorLiteralVariable(
                        name="",
                        type=t,
                        default=val,
                        literal=definition,
                        literal_valid=valid,
                    )
        except SyntaxError:
            pass
        return None
