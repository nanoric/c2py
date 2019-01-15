#encoding: utf-8

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Set

from cxxparser import CXXParseResult, CXXParser, Class, Method
from type import _array_base, _is_array_type, base_types, remove_cvref


class CallbackType(Enum):
    NotCallback = 0  # not a callback
    Direct = 1
    Async = 2


@dataclass
class PreprocessedMethod(Method):
    callback_type: CallbackType = CallbackType.NotCallback


@dataclass
class PreprocessedClass(Class):
    methods: Dict[str, 'PreprocessedMethod'] = field(default_factory=dict)
    need_wrap: bool = False


class PreProcessorResult:

    def __init__(self):
        super().__init__()
        self.dict_classes: Set[str] = set()
        self.const_macros: Dict[str, Any] = {}
        self.classes: Dict[str, PreprocessedClass] = {}


class PreProcessor:

    def __init__(self, parse_result: CXXParseResult):
        self.parser_result = parse_result

    def process(self):
        result = PreProcessorResult()

        # all pod struct to dict
        result.dict_classes = self._find_dict_classes()

        # all error written macros to constant
        result.const_macros = self._pre_process_constant_macros()

        result.classes = self._pre_process_classes(result.dict_classes)
        return result

    def _pre_process_classes(self, dict_classes: Set[str]):
        classes: Dict[str, PreprocessedClass] = {}
        for c in self.parser_result.classes.values():
            gc = PreprocessedClass(**c.__dict__)
            gc.methods = {m.name: PreprocessedMethod(**m.__dict__) for m in gc.methods.values()}
            if c.is_polymorphic:
                gc.need_wrap = True
            classes[gc.name] = gc
        for c in classes.values():
            for m in c.methods.values():
                if m.is_virtual:
                    m.callback_type = CallbackType.Async

        return classes

    def _pre_process_constant_macros(self):
        macros = {}
        for name, definition in self.parser_result.macros.items():
            value = PreProcessor._try_convert_to_constant(definition)
            if value:
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
            return self._to_basic_type_combination(self.parser_result.typedefs[t])
        except KeyError:
            return t

    def _is_basic_type(self, t: str):
        basic_combination = self._to_basic_type_combination(t)

        # just a basic type, such as int, char, short, double etc.
        if basic_combination in base_types:
            return True

        # array of basic type, such as int[], char[]
        if _is_array_type(basic_combination) \
                and _array_base(basic_combination) in base_types:
            return True

        print(basic_combination)
        return False

    def _can_convert_to_dict(self, c: Class):
        # first: no methods
        if c.methods:
            return False

        # second: all variables are basic
        for v in c.variables.values():
            if not self._is_basic_type(v.type):
                return False

        return True

    @staticmethod
    def _try_convert_to_constant(definition: str):
        definition = definition.strip()
        try:
            if definition:
                if definition[0].isdigit():
                    return ast.parse(definition)
                if definition[0] == '"':
                    return ast.parse(definition)
                if definition[0] == "'":
                    return CXXParser.character_literal_to_int(definition[1:-1])
        except SyntaxError:
            return
