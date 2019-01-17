import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from TextHolder import Indent, TextHolder
from cxxparser import CXXParser, Function, Variable, Enum, LiteralVariable
from preprocessor import PreProcessor, PreprocessedClass, PreprocessedMethod
from type import array_base, is_array_type, remove_cvref, is_pointer_type, pointer_base

logger = logging.getLogger(__file__)


def _read_file(name: str):
    with open(name, "rt") as f:
        return f.read()


def render_template(template: str, **kwargs):
    for key, replacement in kwargs.items():
        template = template.replace(f"${key}", str(replacement))
    return template


def default_includes():
    return ['ctp/ThostFtdcTraderApi.h']


@dataclass
class GeneratorOptions:
    typedefs: Dict[str, str]
    constants: Dict[str, Variable]  # to global value
    functions: Dict[str, Function]  # to def
    classes: Dict[str, PreprocessedClass]  # to class
    dict_classes: Set[str]  # to dict
    enums: Dict[str, Enum] = field(default_factory=dict)
    includes: List[str] = field(default_factory=default_includes)
    split_in_files: bool = True
    module_name: str = 'vnctptd'


cpp_str_bases = {'char', 'wchar_t', 'char8_t', 'char16_t', 'char32_t'}
cpp_base_type_to_python_map = {
    'char8_t': "int", 'char16_t': "int", 'char32_t': "int", 'wchar_t': "int",
    'char': 'int', 'short': 'int', 'int': 'int', 'long': 'int',
    'long long': 'int',
    'unsigned char': 'int', 'unsigned short': 'int', 'unsigned int': 'int',
    'unsigned long': 'int', 'unsigned long long': 'int',
    'float': 'float', 'double': 'float',
    'bool': 'bool',
    'void': 'None',
}
python_type_to_pybind11 = {
    'int': 'int_',
    'float': 'float_',
    'str': 'str',
    'None': 'none',
}


def cpp_base_type_to_python(t: str):
    if is_pointer_type(t):
        if pointer_base(t) in cpp_str_bases:
            return 'str'
    if is_array_type(t):
        if array_base(t) in cpp_str_bases:
            return 'str'
    if t in cpp_base_type_to_python_map:
        return cpp_base_type_to_python_map[t]
    return None


def cpp_base_type_to_pybind11(t: str):
    t = remove_cvref(t)
    return python_type_to_pybind11[cpp_base_type_to_python(t)]


def python_value_to_cpp_literal(val: Any):
    t = type(val)
    if t is str:
        return f'"({val})"'
    if t is int:
        return f'({val})'
    if t is float:
        return f'(double({val}))'


class Generator:
    
    def __init__(self, options: GeneratorOptions):
        self.options = options
        
        self.template_dir = "templates"
        
        self.saved_files = {}
    
    def generate(self):
        
        # all classes
        self._output_wrappers()
        self._output_module()
        self._output_class_declarations()
        self._output_ide_hints()
        
        self._save_template("dispatcher.h")
        self._save_template("property_helper.h")
        self._save_template("wrapper_helper.h")
        
        return self.saved_files
    
    def cpp_variable_to_py_with_hint(self, v: Variable, append='', append_unknown: bool = True):
        cpp_type = self._cpp_type_to_python(v.type)
        default_value = ''
        if v.default:
            default_value = ' = ' + str(v.default)
        if cpp_type:
            return f"{v.name}: {cpp_type}{default_value}{append}"
        if append_unknown:
            return f"{v.name}: {v.type}{default_value}{append}  # unknown what to wrap in py"
        else:
            return f"{v.name}: {v.type}{default_value}{append}"
    
    def _cpp_type_to_python(self, t: str):
        t = remove_cvref(t)
        base_type = cpp_base_type_to_python(t)
        if base_type:
            return base_type
        if is_pointer_type(t):
            t = pointer_base(t)
        while t in self.options.typedefs:
            t = self.options.typedefs[t]
        if t in self.options.classes:
            c = self.options.classes[t]
            if self._should_wrap_as_dict(c):
                return 'dict'
            else:
                return t
        if t in self.options.enums:
            return t
        return cpp_base_type_to_python(t)

    def _should_wrap_as_dict(self, c: PreprocessedClass):
        return c.name in self.options.dict_classes
    
    def _output_ide_hints(self):
        hint_code = TextHolder()
        for c in self.options.classes.values():
            if self._should_output_class_generator(c):
                class_code = TextHolder()
                class_code += f"class {c.name}:" + Indent()
                for ms in c.functions.values():
                    for m in ms:
                        class_code += '\n'
                        if m.is_static:
                            class_code += "@staticmethod"
                            class_code += f"def {m.name}(" + Indent()
                        else:
                            class_code += f"def {m.name}(self, " + Indent()

                        for arg in m.args:
                            class_code += Indent(self.cpp_variable_to_py_with_hint(arg, append=','))
                        cpp_ret_type = self._cpp_type_to_python(m.ret_type)
                        class_code += f") -> {cpp_ret_type if cpp_ret_type else m.ret_type}:"
                        class_code += "\n"
                        class_code += "..."
                        class_code += -1

                for v in c.variables.values():
                    description = self.cpp_variable_to_py_with_hint(v)
                    class_code += f"{description}"

                class_code += "\n"
                class_code += "..."
                class_code += -1
                hint_code += class_code

        for v in self.options.constants.values():
            description = self.cpp_variable_to_py_with_hint(v)
            if description:
                hint_code += f"{description}"

        for e in self.options.enums.values():
            enum_code = TextHolder()
            enum_code += f"class {e.name}:" + Indent()
            for v in e.values.values():
                description = self.cpp_variable_to_py_with_hint(v)
                enum_code += f"{description}"
            enum_code += "..."
            enum_code -= 1

            hint_code += enum_code

        self._save_template(
            template_filename="hint.py",
            output_filename=f"{self.options.module_name}.pyi",
            hint_code=hint_code)
    
    def _output_wrappers(self):
        pyclass_template = _read_file(f'{self.template_dir}/pyclass.h')
        wrappers = ''
        # generate callback wrappers
        for c in self.options.classes.values():
            if self._has_wrapper(c):
                wrapper_code = TextHolder()
                for ms in c.functions.values():
                    for m in ms:
                        # filter all arguments can convert as dict
                        dict_types = self._method_dict_types(m)
                        if m.is_virtual and not m.is_final:
                            function_code = self._generate_callback_wrapper(m,
                                                                            dict_types=dict_types)
                            wrapper_code += Indent(function_code)
                        if dict_types:
                            wrapper_code += self._generate_calling_wrapper(c,
                                                                           m,
                                                                           dict_types=dict_types)
                py_class_code = render_template(pyclass_template,
                                                class_name=c.name,
                                                body=wrapper_code)
                wrappers += py_class_code
        self._save_template(f'wrappers.h', wrappers=wrappers)
    
    def _output_class_declarations(self):
        class_generator_declarations = TextHolder()
        for c in self.options.classes.values():
            class_name = c.name
            if not self._should_wrap_as_dict(c):
                class_generator_function_name = self._generate_class_generator_function_name(
                    class_name)
                class_generator_declarations += f"void {class_generator_function_name}(pybind11::module &m);"
        
        self._save_template(f'class_generators.h',
                            class_generator_declarations=class_generator_declarations,
                            )
    
    def _should_output_class_generator(self, c: PreprocessedClass):
        return not self._should_wrap_as_dict(c)
    
    def _output_module(self):
        
        classes_code, classes_generator_definitions = self._generate_class_code()
        
        constants_code = TextHolder()
        for name, value in self.options.constants.items():
            pybind11_type = cpp_base_type_to_pybind11(value.type)
            literal = python_value_to_cpp_literal(value.default)
            if isinstance(value, LiteralVariable):
                if value.literal_valid:
                    literal = value.literal
            constants_code += Indent(f"""m.add_object("{name}", pybind11::{pybind11_type}({literal}));""")
            
        enums_code = TextHolder()
        for name, e in self.options.enums.items():
            enums_code += 1
            enums_code += f"""py::enum_<{e.full_name}>(m, "{e.name}")""" + Indent()

            for v in e.values.values():
                enums_code += f""".value("{v.name}", {e.full_name_of(v)})"""
            enums_code += ".export_values()"
            enums_code += ";" - Indent()

            enums_code -= 1

        self._save_template(
            template_filename="module.cpp",
            output_filename=f'{self.options.module_name}.cpp',
            classes_generator_definitions=classes_generator_definitions,
            classes_code=classes_code,
            constants_code=constants_code,
            enums_code=enums_code,
        )
    
    def _generate_class_code(self):
        class_template = _read_file(f'{self.template_dir}/class.cpp')
        classes_code = TextHolder()
        classes_generator_definitions = TextHolder()
        # generate class classes_code
        for c in self.options.classes.values():
            class_name = c.name
            if self._should_output_class_generator(c):
                wrapper_class_name = c.name
                class_generator_code = TextHolder()
                class_generator_function_name = self._generate_class_generator_function_name(
                    class_name)
                class_generator_code += f"void {class_generator_function_name}(pybind11::module &m)"
                class_generator_code += "{" + Indent()
                if self._has_wrapper(c):
                    wrapper_class_name = "Py" + c.name
                    if c.destructor is not None and c.destructor.access == 'public':
                        class_generator_code += f"""py::class_<{wrapper_class_name}>(m, "{class_name}")\n"""
                    else:
                        class_generator_code += f"""py::class_<{wrapper_class_name},"""
                        class_generator_code += Indent(f"""std::unique_ptr<{wrapper_class_name},""")
                        class_generator_code += Indent(
                            f"""pybind11::nodelete>>(m, "{class_name}")\n""")
                else:
                    class_generator_code += f"""py::class_<{class_name}>(m, "{class_name}")\n"""
                class_generator_code += 1
                for ms in c.functions.values():
                    if len(ms) == 1:
                        m = ms[0]
                        if m.is_static:
                            class_generator_code += f""".def_static("{m.name}", &{wrapper_class_name}::{m.name})\n"""
                        else:
                            class_generator_code += f""".def("{m.name}", &{wrapper_class_name}::{m.name})\n"""
                    else:
                        for m in ms:
                            if m.is_static:
                                class_generator_code += f""".def_static("{m.name}", &{wrapper_class_name}::{m.name})\n"""
                            else:
                                class_generator_code += f""".def("{m.name}", &{wrapper_class_name}::{m.name})\n"""
                
                for name, value in c.variables.items():
                    class_generator_code += f""".DEF_PROPERTY({class_name}, {name})\n"""
                class_generator_code += ";\n" - Indent()
                class_generator_code += "}" - Indent()
                
                if self.options.split_in_files:
                    self._save_file(f'{class_name}.cpp',
                                    self.render_template(
                                        class_template,
                                        class_generator_definition=class_generator_code)
                                    )
                else:
                    classes_generator_definitions += class_generator_code
                
                class_code = TextHolder()
                class_code += f"{class_generator_function_name}(m);"
                classes_code += Indent(class_code)
        return classes_code, classes_generator_definitions
    
    def _generate_class_generator_function_name(self, class_name):
        class_generator_function_name = f"generate_class_{class_name}"
        return class_generator_function_name
    
    def _has_wrapper(self, c: PreprocessedClass):
        return not self._should_wrap_as_dict(c) and c.is_polymorphic
    
    def _method_dict_types(self, m):
        # filter all arguments can convert as dict
        arg_base_types = set(remove_cvref(i.type) for i in m.args)
        return set(i
                   for i in (arg_base_types & self.options.dict_classes)
                   if self._should_wrap_as_dict(i))
    
    def _generate_callback_wrapper(self, m: PreprocessedMethod, dict_types: set = None):
        # calling_back_code
        ret_type = m.ret_type
        args = m.args
        function_name = m.name
        arguments_signature = ",".join([f"{i.type} {i.name}" for i in args])
        arg_list = ",".join(['this', f'"{function_name}"', *[f"{i.name}" for i in args]])
        
        if m.has_overload:
            cast_expression = f"static_cast<{m.type}>(&{m.full_name})"
        else:
            cast_expression = f"&{m.full_name}"
        
        function_code = TextHolder()
        function_code += f"{ret_type} { function_name }({arguments_signature}) override\n"
        function_code += "{\n" + Indent()
        function_code += f"return callback_wrapper<{cast_expression}>::call(" + Indent()
        function_code += f"{arg_list}"
        function_code += -1
        function_code += f");"
        function_code += "}\n" - Indent()
        
        return function_code
    
    def _generate_calling_wrapper(self, c, m, dict_types: set = None):
        return ""
        pass
    
    def _save_template(self, template_filename: str, output_filename: str = None, **kwargs):
        template = _read_file(f'{self.template_dir}/{template_filename}')
        if output_filename is None:
            output_filename = template_filename
        return self._save_file(output_filename, self.render_template(template, **kwargs))
    
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
    r1.dict_classes.clear()
    
    constants = r0.variables
    constants.update(r1.const_macros)
    constants = {k:v for k, v in constants.items() if not k.startswith('_')}
    
    functions = r0.functions
    classes = r1.classes
    
    # make all api "final" to improve performance
    for c in classes.values():
        type = c.name[-3:]
        if type == "Api":
            for ms in c.functions.values():
                for m in ms:
                    if m.is_virtual:
                        m.is_pure_virtual = False
                        m.is_final = True
        elif type == 'Spi':
            for ms in c.functions.values():
                for m in ms:
                    m.is_virtual = True
                    # m.is_pure_virtual = True
                    m.is_final = False
    
    options = GeneratorOptions(
        typedefs=r0.typedefs,
        constants=constants,
        functions=functions,
        classes=classes,
        dict_classes=r1.dict_classes,
        enums=r0.enums,
    )
    
    saved_files = Generator(options=options).generate()
    output_folder = "./generated_files"
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    for name, data in saved_files.items():
        with open(f"{output_folder}/{name}", "wt") as f:
            f.write(data)


if __name__ == '__main__':
    main()
