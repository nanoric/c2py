# encoding: utf-8

import ast
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .cxxparser import (CXXFileParser, CXXParseResult, Class, Enum, Function, LiteralVariable,
                        Method, Namespace, Variable)
from .type import array_base, base_types, is_array_type, is_function_type

"""
42          - dec
0b101010    - bin
052         - oct
0xaa        - hex
0Xaa        - hex
1234u       - suffix
1234ull     - suffix
145'920     - with single quotes
1.0         - double
1.0f        - float

ignore:
5.9604644775390625e-8F16
'123123'

unsuportted:
1e10        - science
1E10        - science
1e+10
1e-10
1E-10
1E+10

"""
cpp_digit_re = re.compile(
    "(0b[01]+|0[0-7]+|0[Xx][0-9a-fA-F]+|[0-9']*[0-9]+)((ull)|(ULL)|(llu)|(LLU)|(ul)|(UL)|(ll)|(LL)|[UuLl])?$"
)

cpp_digit_suffix_types = {
    "u": "unsigned int",
    "l": "long",
    "ul": "usngined long",
    "ll": "long long",
    "ull": "unsigned long long",
    "llu": "unsigned long long",
    "f": "float",
}
cpp_digit_suffix_types.update(
    {k.upper(): v for k, v in cpp_digit_suffix_types.items()}
)


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
    name: str = ""
    parent: "Namespace" = None

    alias: str = ""
    enums: Dict[str, "GeneratorEnum"] = field(default_factory=dict)
    typedefs: Dict[str, str] = field(default_factory=dict)
    classes: Dict[str, "GeneratorClass"] = field(default_factory=dict)
    variables: Dict[str, "GeneratorVariable"] = field(default_factory=dict)
    functions: Dict[str, List["GeneratorFunction"]] = field(
        default_factory=(lambda: defaultdict(list))
    )

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name
        self.classes = {
            name: GeneratorClass(**oc.__dict__)
            for name, oc in self.classes.items()
        }
        self.enums = {
            name: GeneratorEnum(**oc.__dict__)
            for name, oc in self.enums.items()
        }
        self.variables = {
            name: GeneratorVariable(**oc.__dict__)
            for name, oc in self.variables.items()
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


@dataclass
class GeneratorFunction(Function, GeneratorNamespace):
    name: str = ''
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
    name: str = ''
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
class GeneratorMethod(Method, GeneratorNamespace):
    name: str = ''
    ret_type: str = ''
    parent: Class = None
    has_overload: bool = False


@dataclass
class GeneratorClass(Class, GeneratorNamespace):
    name: str = ''
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
    remove_slash_prefix: bool = True
    find_dict_class: bool = False
    caster_options: CasterOptions = CasterOptions


@dataclass
class PreProcessorResult(Namespace):
    dict_classes: Set[str] = field(default_factory=set)
    const_macros: Dict[str, Variable] = field(default_factory=dict)
    functions: Dict[str, List[GeneratorFunction]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    classes: Dict[str, GeneratorClass] = field(default_factory=dict)
    enums: Dict[str, GeneratorEnum] = field(default_factory=dict)
    caster_class: GeneratorClass = None


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

        # all pod struct to dict
        # todo: generator doesn't support dict class currently
        if self.options.find_dict_class:
            self.dict_classes = self._find_dict_classes()
            result.dict_classes = self.dict_classes

        self.process_typedefs()
        # classes

        # functions
        self._process_functions(result)

        # classes
        result.classes = self._process_classes(self.parser_result.classes)

        # all error written macros to constant
        result.const_macros = self._process_constant_macros()

        self._wrap_c_function_pointers_for_namespace(result)
        for c in result.classes.values():
            self._wrap_c_function_pointers_for_namespace(c)
        result.enums = self._process_enums()

        # caster
        if self.options.caster_options.enable:
            caster: GeneratorClass = self._process_caster(result.classes)
            result.caster_class = caster

        return result

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

    def _wrap_c_function_pointers_for_namespace(self, n: Namespace):
        for ms in n.functions.values():
            for m in ms:
                self._wrap_c_function_pointers(m)
        for c in n.classes.values():
            self._wrap_c_function_pointers_for_namespace(c)

    def _wrap_c_function_pointers(self, m: Function):
        for i, a in enumerate(m.args):
            if (
                is_function_type(self._to_basic_type_combination(a.type)) and
                self._to_basic_type_combination(m.args[i + 1].type) == 'void *'
            ):
                args = m.args

                # remove user supplied argument
                m.args = args[:i + 1] + args[i + 2:]

                t = m.args[i].type
                m.args[i].type = t.replace(", void *)", ")")

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
        if self.options.remove_slash_prefix:
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
        f.args = [GeneratorVariable(**ov.__dict__, alias=ov.name) for ov in f.args]
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
    def _try_parse_cpp_digit_literal(literal: str):
        m = cpp_digit_re.match(literal)
        if m:
            digit = m.group(1)
            suffix = m.group(2)
            val = ast.literal_eval(digit.replace("'", ""))
            t = "int"
            if suffix:
                t = cpp_digit_suffix_types[suffix]
            return GeneratorLiteralVariable(
                name="", type=t, default=val, literal=literal
            )
        return None

    @staticmethod
    def _try_convert_to_constant(definition: str) -> Optional[GeneratorLiteralVariable]:
        definition = definition.strip()
        try:
            if definition:
                var = PreProcessor._try_parse_cpp_digit_literal(definition)
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
