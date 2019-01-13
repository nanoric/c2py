import ast
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set

from cxxparser import CXXParseResult, CXXParser, Class, Function, Method, Variable

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


def _is_array_type(t: str):
    return '[' in t


def _array_base(t: str):
    """
    :raise ValueError if t is not a array type
    """
    return t[:t.index('[') - 1]


def _is_pointer_type(t: str):
    return "*" in t


def _is_reference_type(t: str):
    return "&" in t


def remove_cvref(t: str):
    return t.replace("const ", "").replace("*", "").replace("&", "").replace(" ", "")


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
    methods: Dict[str, 'GMethod'] = field(default_factory=dict)


def default_includes():
    return []


@dataclass
class GeneratorOptions:
    constants: Dict[str, Any]  # to global value
    functions: Dict[str, Function]  # to def
    classes: Dict[str, GClass]  # to class
    dict_classes: Set[str]  # to dict
    includes: List[str] = field(default_factory=default_includes)


class Generator:
    
    def __init__(self, options: GeneratorOptions):
        self.options = options

        self.template_dir = "templates"

        self.saved_files = {'helper.h': _read_file(f'{self.template_dir}/helper.h')}
    
    def generate(self):
        module_name = 'vnctptd'

        # all classes
        wrapper_code = self._generate_wrappers()
        class_code = self._generate_class()

        self._save_file(f'{module_name}.cpp', class_code)
        self._save_file(f'wrapper.h', wrapper_code)
        # self._save_file(f'converts.h', converts_code)
        return self.saved_files

    def _generate_class(self):
        module_template = _read_file(f'{self.template_dir}/module.cpp')
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
                        module_code += f"""		.def("{m.name}", &{py_class_name}::{m.name})\n"""
                for name, value in c.variables:
                    module_code += f"""		DEF_PROPERTY({class_name}, {name})\n"""
                module_code += "        ;\n"
                module_body += module_code
        return self.render_template(module_template, module_body=module_body)

    def _generate_wrappers(self):
        wrapper_template = _read_file(f'{self.template_dir}/wrapper.h')
        pyclass_template = _read_file(f'{self.template_dir}/pyclass.h')
        wrappers = ''
        # generate callback wrappers
        for c in self.options.classes.values():
            if c.name not in self.options.dict_classes:
                wrapper_code = ""
                for m in c.methods.values():
                    # filter all arguments can convert as dict
                    dict_types = self._method_dict_types(m)
                    if m.is_virtual and not m.is_final:
                        function_code = self._generate_callback_wrapper(c, m, dict_types=dict_types)
                        wrapper_code += function_code
                    if dict_types:
                        wrapper_code += self._generate_calling_wrapper(c, m, dict_types=dict_types)
                py_class_code = render_template(pyclass_template,
                                                class_name=c.name,
                                                body=wrapper_code)
                wrappers += py_class_code
        return self.render_template(wrapper_template, wrappers=wrappers)

    def _method_dict_types(self, m):
        # filter all arguments can convert as dict
        arg_base_types = set(remove_cvref(i.type) for i in m.args.values())
        return arg_base_types & self.options.dict_classes

    def _generate_callback_wrapper(self, c, m, dict_types: set = None):
        overload_symbol = "PYBIND11_OVERLOAD_PURE" if m.is_pure_virtual else "PYBIND11_OVERLOAD"

        # dereference all pointers in arguments
        deref_args: List[Variable] = []
        deref_code = ""
        for i in m.args.values():
            if _is_pointer_type(i.type):
                # if this is also a type can convert to dict, don't use reference
                ref_signature = '&' if remove_cvref(i.type) not in dict_types else ''
                new_name = "_" + i.name
                deref_args.append(Variable(name=new_name, type=i.type))
                deref_code += f"        auto {ref_signature}{new_name} = *{i.name};\n"
            else:
                deref_args.append(i)

        # check if there are any arguments can be convert to a dict
        if dict_types:
            # with dict conversion, callback is huge different from normal

            dict_args = {
                arg.name: arg
                for arg in deref_args
                if remove_cvref(arg.type) in dict_types
            }

            # generate callback code
            convert_code = ''
            for name, arg in dict_args.items():
                # convert that structure as dict
                py_name = "py_" + name
                convert_code += f"		pybind11::dict {py_name};\n"
                arg_class = self.options.classes[remove_cvref(arg.type)]

                # for every variable, assign its dict key
                for v in arg_class.variables.values():
                    convert_code += f"""        {py_name}["{v.name}"] = {name}.{v.name};\n"""
                convert_code += "\n"

            # generate arguments name list
            forward_args = ",".join([i.name if i.type not in dict_types else "py_" + i.name
                                     for i in m.args.values()])

            callback = f"""{convert_code}"""
            callback += f"""        {overload_symbol}({m.ret_type}, {c.name}, {m.name}, {forward_args});\n"""
        else:
            forward_args = ",".join([i.name for i in m.args.values()])
            callback = f"""        {overload_symbol}({m.ret_type}, {c.name}, {m.name}, {forward_args});\n"""

        # callback
        callback_type = m.callback_type if isinstance(m,
                                                      GMethod) else CallbackType.Async
        arguments_signature = ",".join([f"{i.type} {i.name}" for i in m.args.values()])
        if callback_type == CallbackType.Direct:
            function_code = f"""    {m.ret_type} {m.name}({arguments_signature}) override {{\n"""
            function_code += f"""{deref_code}"""
            function_code += f"""{callback}"""
            function_code += f"""    }}\n"""
        elif callback_type == CallbackType.Async:
            function_code = f"""    {m.ret_type} {m.name}({arguments_signature}) override {{\n"""
            function_code += f"""{deref_code}"""
            function_code += f"""        auto func = [=](){{\n"""
            function_code += f"""{callback}"""
            function_code += f"""       }};\n"""
            function_code += f"""       AsyncDispatcher::instance().add(std::move(func));\n"""
            function_code += f"""    }}\n"""
        else:
            logger.error("%s", f'unknown callback type: {m.callback_type}')
            function_code = ''

        return function_code

    def _generate_calling_wrapper(self, c, m, dict_types: set = None):
        
        pass

    def _save_file(self, filename, data):
        self.saved_files[filename] = data

    def render_template(self, templates, **kwargs):
        kwargs['includes'] = self._generate_includes()
        return render_template(templates, **kwargs)

    def _generate_includes(self):
        code = ""
        for i in self.options.includes:
            code += f"""#include "{i}"\n"""
        return code


def main():
    r0 = CXXParser("ctpapi/a.cpp").parse()
    r1 = PreProcessor(r0).process()
    
    constants = r0.constants
    constants.update(r1.const_macros)
    
    functions = r0.functions
    classes = r0.classes

    # make all api "final" to improve performance
    for c in classes.values():
        type = c.name[-3:]
        if type == "Api":
            for m in c.methods.values():
                if m.is_virtual:
                    m.is_pure_virtual = False
                    m.is_final = True
        elif type == 'Spi':
            for m in c.methods.values():
                m.is_virtual = True
                # m.is_pure_virtual = True
                m.is_final = False

    options = GeneratorOptions(
        constants=constants,
        functions=functions,
        classes=classes,
        dict_classes=r1.dict_classes,
    )

    saved_files = Generator(options=options).generate()
    output_folder = "./generated_files"
    for name, data in saved_files.items():
        with open(f"{output_folder}/{name}", "wt") as f:
            f.write(data)


if __name__ == '__main__':
    main()
