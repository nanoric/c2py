import ast
import os
from typing import Any, Dict, Set

from cxxparser import CXXParseResult, CXXParser, Class

base_types = ['char8_t', 'char16_t', 'char32_t', 'wchar_t',
              'char', 'short', 'int', 'long',
              'long long'
              'unsigned char', 'unsigned short', 'unsigned int',
              'unsigned long', 'unsigned long long',
              'float', 'double',
              ]


class PreProcessorResult:

    def __init__(self):
        super().__init__()
        self.dict_classes: Set[str] = set()
        self.const_macros: Dict[str, Any] = {}


class PreProcessor:

    def __init__(self, parse_result: CXXParseResult):
        self.parse_result = parse_result

    def process(self):
        result = PreProcessorResult()

        # all pod struct to dict
        for c in self.parse_result.classes.values():
            if self._can_convert_to_dict(c):
                result.dict_classes.add(c.name)

        # all error written macros to constant
        for name, definition in self.parse_result.macros.items():
            value = PreProcessor._try_convert_to_constant(definition)
            if value:
                result.const_macros[name] = value
        return result

    def _to_basic_type_combination(self, t: str):
        try:
            return self._to_basic_type_combination(self.parse_result.typedefs[t])
        except KeyError:
            return t

    def _is_basic_type(self, t: str):
        basic_combination = self._to_basic_type_combination(t)

        # just a basic type, such as int, char, short, double etc.
        if basic_combination in base_types:
            return True

        # array of basic type, such as int[], char[]
        if PreProcessor._is_array_type(basic_combination) \
                and PreProcessor._array_base(basic_combination) in base_types:
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

    @staticmethod
    def _is_array_type(t: str):
        return '[' in t

    @staticmethod
    def _array_base(t: str):
        """
        :raise ValueError if t is not a array type
        """
        return t[:t.index('[') - 1]


class Generator:

    def __init__(self, r0: CXXParseResult, r1: PreProcessorResult):
        self.r0 = r0
        self.r1 = r1

    def generate(self):
        module_name = 'vnctptd'
        # all classes
        body = ''
        for c in self.r0.classes.values():
            code = ""
            if c.name not in self.r1.dict_classes:
                code += f"""py::class_<{c.name}>(m, "{c.name}")"""
                for m in c.methods.values():
                    if m.static:
                        code += f"""		.def_static("{m.name}", &{c.name}::{m.name})\n"""
                    else:
                        code += f"""		.def("{m.name}", &{c.name}::{m.name})\n"""
                    # todo: constructor and destructor
                for name, value in c.variables:
                    code += f"""		DEF_PROPERTY({c.name}, {name})\n"""
                code += "        ;\n"
            else:
                pass
            body += code

        with open('source.cpp', 'rt') as f:
            template = f.read()
            result = template.replace("$body", body)
        output_dir = "generated_files"
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        with open(f"{output_dir}/{module_name}.cpp", "wt") as f:
            f.write(result)


def main():
    r0 = CXXParser("ctpapi/a.cpp").parse()
    r1 = PreProcessor(r0).process()
    Generator(r0, r1).generate()


if __name__ == '__main__':
    main()
