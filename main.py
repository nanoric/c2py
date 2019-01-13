import ast
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Set

from cxxparser import CXXParseResult, CXXParser, Class, Function, Method

logger = logging.getLogger(__file__)

base_types = ['char8_t', 'char16_t', 'char32_t', 'wchar_t',
              'char', 'short', 'int', 'long',
              'long long'
              'unsigned char', 'unsigned short', 'unsigned int',
              'unsigned long', 'unsigned long long',
              'float', 'double',
              ]


def _read_file(name: str):
    with open(name, "rt") as f:
        return f.read()


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


class CallbackType(Enum):
    NotCallback = 0  # not a callback
    Direct = 1
    Async = 2


@dataclass
class GMethod(Method):
    callback_type: CallbackType = CallbackType.NotCallback


@dataclass
class GClass(Class):
    methods: Dict[str, 'GMethod'] = dict


@dataclass
class GeneratorOptions:
    constants: Dict[str, Any]  # to global value
    functions: Dict[str, Function]  # to def
    classes: Dict[str, GClass]  # to class
    dict_classes: Set[str]  # to dict


class Generator:
    
    def __init__(self, options: GeneratorOptions):
        self.options = options
        
        template_dir = "templates"
        self.module_template = _read_file(f'{template_dir}/module.cpp')
        self.pyclass_template = _read_file(f'{template_dir}/pyclass.h')
        self.helper_code = _read_file(f'{template_dir}/helper.h')
        self.wrapper_template = _read_file(f'{template_dir}/wrapper.h')
        
        self.saved_files = {}
    
    def generate(self):
        module_name = 'vnctptd'
        
        # all classes
        self._generate_wrappers()
        self._generate_class()
        self._generate_converts()
        return self.saved_files

    def _generate_class(self):
        module_body = ''
        # generate class module_body
        for c in self.options.classes.values():
            class_name = c.name
            if c.name not in self.options.dict_classes:
                py_class_name = "Py" + c.name
                module_code = f"""    py::class_<{class_name}, {py_class_name}>(m, "{class_name}")\n"""
                for m in c.methods.values():
                    if m.is_static:
                        module_code += f"""		.def_static("{m.name}", &{py_class_name}::{m.name})\n"""
                    else:
                        module_code += f"""		.def("{m.name}", &{class_name}::{m.name})\n"""
                for name, value in c.variables:
                    module_code += f"""		DEF_PROPERTY({class_name}, {name})\n"""
                module_code += "        ;\n"
                module_body += module_code
        self._save_file(f'{module_name}.cpp', render_template(self.module_template,
                                                              module_body=module_body))

    def _generate_wrappers(self):
        wrappers = ''
        # generate callback wrappers
        for c in self.options.classes.values():
            if c.name not in self.options.dict_classes:
                wrapper_code = ""
                for m in c.methods.values():
                    if m.is_virtual:
                        callback_type = m.callback_type if isinstance(m,
                                                                      GMethod) else CallbackType.Async
                        if callback_type == CallbackType.Direct:
                            args_str = ",".join([f"{i.type} {i.name}" for i in m.args.values()])
                            forward_args = ",".join([i.name for i in m.args.values()])
                            wrapper_code += f"""    {m.ret_type} {m.name}({args_str}) override {{ PYBIND11_OVERLOAD({m.ret_type}, {c.name}, {m.name}, {forward_args}); }}\n"""
                        elif callback_type == CallbackType.Async:
                            args_str = ",".join([f"{i.type} {i.name}" for i in m.args.values()])
                            forward_args = ",".join([i.name for i in m.args.values()])
                            wrapper_code += f"""    {m.ret_type} {m.name}({args_str}) override {{ PYBIND11_OVERLOAD({m.ret_type}, {c.name}, {m.name}, {forward_args}); }}\n"""
                        else:
                            logger.error("%s", f'unknown callback type: {m.callback_type}')
                py_class_code = render_template(self.pyclass_template,
                                                class_name=c.name,
                                                body=wrapper_code)
                wrappers += py_class_code
        self._save_file(f'wrapper.h', render_template(self.wrapper_template,
                                                      wrappers=wrappers))

    def _save_file(self, filename, data):
        self.saved_files[filename] = data

    def _generate_converts(self):
        converts = ''
        for c in self.options.classes.values():
            if c.name in self.options.dict_classes:
            
        pass


def main():
    r0 = CXXParser("ctpapi/a.cpp").parse()
    r1 = PreProcessor(r0).process()
    
    constants = r0.constants
    constants.update(r1.const_macros)
    
    functions = r0.functions
    classes = r0.classes
    
    options = GeneratorOptions(
        constants=constants,
        functions=functions,
        classes=classes,
        dict_classes=r1.dict_classes,
    )
    
    Generator(options=options).generate()


if __name__ == '__main__':
    main()
