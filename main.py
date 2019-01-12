import ast
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Set

from cxxparser import CXXParseResult, CXXParser, Class, Method

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


def render_template(template: str, **kwargs):
    for key, replacement in kwargs.items():
        template = template.replace(f"${key}", replacement)
    return template


class Generator:

    def __init__(self, r0: CXXParseResult, r1: PreProcessorResult):
        self.r0 = r0
        self.r1 = r1

        self.callback_re = re.compile("Spi::On\w+")
        self.output_dir = "generated_files"

        template_dir = "templates"
        with open(f'{template_dir}/module.cpp', 'rt') as f:
            self.module_template = f.read()

        with open(f'{template_dir}/pyclass.h', 'rt') as f:
            self.pyclass_template = f.read()

    def generate(self):
        module_name = 'vnctptd'

        # all classes
        body = ''
        header = ''

        # generate wrappers
        for c in self.r0.classes.values():
            if c.name not in self.r1.dict_classes:
                wrapper_code = ""
                for m in c.methods.values():
                    if self.is_callback(m.full_signature):
                        args_str = ",".join([f"{i.type} {i.name}" for i in m.args.values()])
                        forward_args = ",".join([i.name for i in m.args.values()])
                        wrapper_code += f"""    {m.ret_type} {m.name}({args_str}) override {{ PYBIND11_OVERLOAD({m.ret_type}, {c.name}, {m.name}, {forward_args}); }}\n"""
                py_class_code = render_template(self.pyclass_template,
                                                ClassName=c.name,
                                                body=wrapper_code)
                header += py_class_code

        # generate class body
        for c in self.r0.classes.values():
            class_name = c.name
            if c.name not in self.r1.dict_classes:
                py_class_name = "Py" + c.name
                module_code = f"""    py::class_<{class_name}, {py_class_name}>(m, "{class_name}")\n"""
                for m in c.methods.values():
                    if not self.is_callback(m.full_signature):
                        if m.static:
                            module_code += f"""		.def_static("{m.name}", &{py_class_name}::{m.name})\n"""
                        else:
                            module_code += f"""		.def("{m.name}", &{py_class_name}::{m.name})\n"""
                for name, value in c.variables:
                    module_code += f"""		DEF_PROPERTY({class_name}, {name})\n"""
                module_code += "        ;\n"
                body += module_code

        result = render_template(self.module_template, body=body)

        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        self.write_file(f'{module_name}.cpp', result)
        self.write_file(f'wrapper.h', "#pragma once\n\n" + header)

    def write_file(self, filename, data):
        with open(f"{self.output_dir}/{filename}", "wt") as f:
            f.write(data)

    def is_callback(self, name: str):
        return self.callback_re.search(name)


def main():
    r0 = CXXParser("ctpapi/a.cpp").parse()
    r1 = PreProcessor(r0).process()
    Generator(r0, r1).generate()


if __name__ == '__main__':
    main()
