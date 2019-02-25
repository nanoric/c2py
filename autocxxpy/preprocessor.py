# encoding: utf-8

import ast
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

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

@dataclass
class GeneratorFunction(Function):
    alias: str = ""

@dataclass
class GeneratorMethod(Method):
    alias: str = ""
    has_overload: bool = False


@dataclass
class GeneratorClass(Class):
    functions: Dict[str, List[GeneratorMethod]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    need_wrap: bool = False  # if need_wrap is true, wrap this to dict
    # generator will not assign python constructor for pure virtual
    is_pure_virtual: bool = False


@dataclass
class PreProcessorOptions:
    parse_result: CXXParseResult
    remove_slash_prefix: bool = True
    find_dict_class: bool = False


@dataclass
class PreProcessorResult(Namespace):
    dict_classes: Set[str] = field(default_factory=set)
    const_macros: Dict[str, Variable] = field(default_factory=dict)
    functions: Dict[str, List[GeneratorFunction]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    classes: Dict[str, GeneratorClass] = field(default_factory=dict)
    enums: Dict[str, Enum] = field(default_factory=dict)


class PreProcessor:

    def __init__(self, options: PreProcessorOptions):
        self.options = options
        self.parser_result = options.parse_result
        self.typedef_reverse: Dict[str, Set[str]] = defaultdict(set)

        self.easy_names: Dict[str, str] = {}
        self.dict_classes = set()

    def process(self) -> PreProcessorResult:
        result = PreProcessorResult()

        # all pod struct to dict
        # todo: generator doesn't support dict class currently
        if self.options.find_dict_class:
            self.dict_classes = self._find_dict_classes()
            result.dict_classes = self.dict_classes

        self.process_typedefs()
        self._process_easy_names()
        # classes

        # functions
        for name, ms in self.parser_result.functions.items():
            new_ms = [GeneratorFunction(**m.__dict__, alias=self._alias(m)) for m in ms]
            result.functions[name] = new_ms

        # classes
        result.classes = self._pre_process_classes(self.parser_result.classes)

        # all error written macros to constant
        result.const_macros = self._pre_process_constant_macros()

        self._wrap_c_function_pointers_for_namespace(result)
        for c in result.classes.values():
            self._wrap_c_function_pointers_for_namespace(c)
        result.enums = self._pre_process_enums()

        return result

    def process_typedefs(self):
        for name, target in self.parser_result.typedefs.items():
            self.typedef_reverse[target].add(name)

    def _process_easy_names(self):
        for name, alias in self.typedef_reverse.items():
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

    def _pre_process_enums(self):
        enums: Dict[str, Enum] = {}
        for oe in self.parser_result.enums.values():
            e = Enum(**oe.__dict__)
            e.values = {
                name: Variable(**v.__dict__)
                for name, v in oe.values.items()
            }

            self.convert_easy_name(e)
            for v in e.values.values():
                v.type = e.name
            enums[e.name] = e
        return enums

    def _pre_process_classes(self, ocs: Dict):
        classes: Dict[str, GeneratorClass] = {}
        for oc in ocs.values():
            c = self._pre_process_class(oc)
            classes[c.name] = c

        return classes

    def _alias(self, m):
        alias = m.name
        if self.options.remove_slash_prefix:
            while alias.startswith('_'):
                alias = alias[1:]
        return alias

    def _pre_process_class(self, oc):
        c = GeneratorClass(**oc.__dict__)
        c.functions = {
            name: [GeneratorMethod(**m.__dict__, alias=self._alias(m)) for m in ms]
            for name, ms in oc.functions.items()
        }
        c.classes = self._pre_process_classes(oc.classes)
        self.convert_easy_name(c)
        if c.is_polymorphic:
            c.need_wrap = True
        for ms in c.functions.values():

            # check overload
            if len(ms) >= 2:
                for m in ms:
                    m.has_overload = True

            # check pure virtual
            for m in ms:
                if m.is_pure_virtual:
                    c.is_pure_virtual = True
        return c

    def convert_easy_name(self, v: Any):
        if v.name in self.easy_names:
            v.name = self.easy_names[v.name]
        return v

    def _pre_process_constant_macros(self):
        macros = {}
        for name, definition in self.parser_result.macros.items():
            value = PreProcessor._try_convert_to_constant(definition)
            if value is not None:
                value.name = name
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
            return LiteralVariable(
                name="", type=t, default=val, literal=literal
            )
        return None

    @staticmethod
    def _try_convert_to_constant(definition: str) -> Optional[Variable]:
        definition = definition.strip()
        try:
            if definition:
                var = PreProcessor._try_parse_cpp_digit_literal(definition)
                if var:
                    return var
                val = None
                if definition.startswith('"') and definition.endswith('"'):
                    val = ast.literal_eval(definition)
                    return LiteralVariable(
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
                    return LiteralVariable(
                        name="",
                        type=t,
                        default=val,
                        literal=definition,
                        literal_valid=valid,
                    )
        except SyntaxError:
            pass
        return None
