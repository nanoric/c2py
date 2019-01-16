import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from TextHolder import Ident, TextHolder
from cxxparser import CXXParser, Function, Variable
from preprocessor import CallbackType, PreProcessor, PreprocessedClass
from type import _array_base, _is_array_type, _is_pointer_type, remove_cvref

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
    constants: Dict[str, Any]  # to global value
    functions: Dict[str, Function]  # to def
    classes: Dict[str, PreprocessedClass]  # to class
    dict_classes: Set[str]  # to dict
    includes: List[str] = field(default_factory=default_includes)
    split_in_files: bool = True
    module_name: str = 'vnctptd'


cpp_str_bases = {'char', 'wchar_t', 'char8_t', 'char16_t', 'char32_t'}
cpp_base_type_to_python = {
    'char8_t': "int", 'char16_t': "int", 'char32_t': "int", 'wchar_t': "int",
    'char': 'int', 'short': 'int', 'int': 'int', 'long': 'int',
    'long long': 'int',
    'unsigned char': 'int', 'unsigned short': 'int', 'unsigned int': 'int',
    'unsigned long': 'int', 'unsigned long long': 'int',
    'float': 'float', 'double': 'float',
    'void': 'None'
}


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
        if cpp_type:
            return f"{v.name}: {cpp_type}{append}"
        if append_unknown:
            return f"{v.name}: {v.type}{append}  # unknown what to wrap in py"
        else:
            return f"{v.name}: {v.type}{append}"
    
    def _cpp_type_to_python(self, t: str):
        t = remove_cvref(t)
        if _is_array_type(t):
            if _array_base(t) in cpp_str_bases:
                return 'str'
        if t in self.options.classes:
            c = self.options.classes[t]
            if self._should_wrap_as_dict(c):
                return 'dict'
            else:
                return t
        if t in cpp_base_type_to_python:
            return cpp_base_type_to_python[t]
        return None
    
    def _should_wrap_as_dict(self, c: PreprocessedClass):
        return c.name in self.options.dict_classes
    
    def _output_ide_hints(self):
        hint_code = TextHolder()
        for c in self.options.classes.values():
            if self._should_output_class_generator(c):
                class_code = TextHolder()
                class_code += f"class {c.name}:" + Ident()
                for m in c.methods.values():
                    class_code += '\n'
                    if m.is_static:
                        class_code += "@staticmethod"
                        class_code += f"def {m.name}(" + Ident()
                    else:
                        class_code += f"def {m.name}(self, " + Ident()
                    
                    for arg in m.args.values():
                        class_code += Ident(self.cpp_variable_to_py_with_hint(arg, append=','))
                    cpp_ret_type = self._cpp_type_to_python(m.ret_type)
                    class_code += f") -> {cpp_ret_type if cpp_ret_type else m.ret_type}:"
                    class_code += "\n"
                    class_code += "..."
                    class_code += -1
                
                class_code += "\n"
                class_code += "..."
                class_code += -1
                hint_code += class_code
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
                for m in c.methods.values():
                    # filter all arguments can convert as dict
                    dict_types = self._method_dict_types(m)
                    if m.is_virtual and not m.is_final:
                        function_code = self._generate_callback_wrapper(c, m, dict_types=dict_types)
                        wrapper_code += Ident(function_code)
                    if dict_types:
                        wrapper_code += self._generate_calling_wrapper(c, m, dict_types=dict_types)
                py_class_code = render_template(pyclass_template,
                                                class_name=c.name,
                                                body=wrapper_code)
                wrappers += py_class_code
        self._save_template(f'wrapper.h', wrappers=wrappers)
    
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
        class_template = _read_file(f'{self.template_dir}/class.cpp')

        module_body = TextHolder()
        classes_generator_definitions = TextHolder()
        # generate class module_body
        for c in self.options.classes.values():
            class_name = c.name
            if self._should_output_class_generator(c):
                wrapper_class_name = c.name
                class_generator_code = TextHolder()
                class_generator_function_name = self._generate_class_generator_function_name(
                    class_name)
                class_generator_code += f"void {class_generator_function_name}(pybind11::module &m)"
                class_generator_code += "{" + Ident()
                if self._has_wrapper(c):
                    wrapper_class_name = "Py" + c.name
                    if c.destructor is not None and c.destructor.access == 'public':
                        class_generator_code += f"""py::class_<{wrapper_class_name}>(m, "{class_name}")\n"""
                    else:
                        class_generator_code += f"""py::class_<{wrapper_class_name},"""
                        class_generator_code += Ident(f"""std::unique_ptr<{wrapper_class_name},""")
                        class_generator_code += Ident(
                            f"""pybind11::nodelete>>(m, "{class_name}")\n""")
                else:
                    class_generator_code += f"""py::class_<{class_name}>(m, "{class_name}")\n"""
                class_generator_code += 1
                for m in c.methods.values():
                    if m.is_static:
                        class_generator_code += f""".def_static("{m.name}", &{wrapper_class_name}::{m.name})\n"""
                    else:
                        class_generator_code += f""".def("{m.name}", &{wrapper_class_name}::{m.name})\n"""
                for name, value in c.variables.items():
                    class_generator_code += f""".DEF_PROPERTY({class_name}, {name})\n"""
                class_generator_code += ";\n" - Ident()
                class_generator_code += "}" - Ident()
                
                if self.options.split_in_files:
                    self._save_file(f'{class_name}.cpp',
                                    self.render_template(
                                        class_template,
                                        class_generator_definition=class_generator_code)
                                    )
                else:
                    classes_generator_definitions += class_generator_code
                
                module_code = TextHolder()
                module_code += f"{class_generator_function_name}(m);"
                module_body += Ident(module_code)
        self._save_template(
            template_filename="module.cpp",
            output_filename=f'{self.options.module_name}.cpp',
            classes_generator_definitions=classes_generator_definitions,
            module_body=module_body,
        )

    def _generate_class_generator_function_name(self, class_name):
        class_generator_function_name = f"generate_class_{class_name}"
        return class_generator_function_name
    
    def _has_wrapper(self, c: PreprocessedClass):
        return not self._should_wrap_as_dict(c) and c.is_polymorphic
    
    def _method_dict_types(self, m):
        # filter all arguments can convert as dict
        arg_base_types = set(remove_cvref(i.type) for i in m.args.values())
        return set(i
                   for i in (arg_base_types & self.options.dict_classes)
                   if self._should_wrap_as_dict(i))
    
    def _generate_callback_wrapper(self, c, m, dict_types: set = None):
        overload_symbol = "PYBIND11_OVERLOAD_PURE" if m.is_pure_virtual else "PYBIND11_OVERLOAD"
        
        # dereference all pointers in arguments
        deref_args: List[Variable] = []
        deref_code = TextHolder()
        for i in m.args.values():
            if _is_pointer_type(i.type):
                # if this is also a type can convert to dict, don't use reference
                # ref_signature = '&' if remove_cvref(i.type) not in dict_types else ''
                ref_signature = ''
                new_name = "_" + i.name
                deref_args.append(Variable(name=new_name, type=i.type))
                deref_code += f"auto {ref_signature}{new_name} = *{i.name};\n"
            else:
                deref_args.append(i)
        
        # check if there are any arguments can be convert to a dict
        # with dict conversion, calling_back_code is huge different from normal
        calling_back_code = TextHolder()
        if dict_types:
            dict_args = {
                arg.name: arg
                for arg in deref_args
                if remove_cvref(arg.type) in dict_types
            }
            
            convert_code = TextHolder()
            # generate calling_back_code code
            for name, arg in dict_args.items():
                # convert that structure as dict
                py_name = "py" + name
                convert_code += f"pybind11::dict {py_name};\n"
                arg_class = self.options.classes[remove_cvref(arg.type)]
                
                # for every variable, assign its dict key
                for v in arg_class.variables.values():
                    convert_code += f"""{py_name}["{v.name}"] = {name}.{v.name};\n"""
                convert_code += "\n"
            
            # generate arguments name list
            forward_args = ",".join([
                ('&' if _is_pointer_type(i.type) else '') + (
                    i.name if i.type not in dict_types else "py" + i.name)
                for i in deref_args])
            
            calling_back_code += f"""{convert_code}"""
            calling_back_code += f"""{overload_symbol}({m.ret_type}, {c.name}, {m.name}, {forward_args});\n"""
        else:
            forward_args = ",".join([
                (
                    f'const_cast<{i.type}>(&{i.name})' if _is_pointer_type(
                        i.type) else i.name) for i in deref_args])
            calling_back_code += f"""{overload_symbol}({m.ret_type}, {c.name}, {m.name}, {forward_args});\n"""
        
        # calling_back_code
        callback_type = m.callback_type
        arguments_signature = ",".join([f"{i.type} {i.name}" for i in m.args.values()])
        function_code = TextHolder()
        if callback_type == CallbackType.Direct:
            function_code += f"""{m.ret_type} {m.name}({arguments_signature}) override\n"""
            function_code += """{\n""" + Ident()
            function_code += deref_code
            function_code += calling_back_code
            function_code += "}\n" - Ident()
        elif callback_type == CallbackType.Async:
            function_code += f"""{m.ret_type} {m.name}({arguments_signature}) override\n"""
            function_code += """{\n""" + Ident()
            function_code += deref_code
            function_code += f"""auto task = [=]()\n"""
            function_code += """{\n""" + Ident()
            function_code += calling_back_code
            function_code += "};\n" - Ident()
            function_code += f"""AsyncDispatcher::instance().add(std::move(task));\n"""
            function_code += "}\n" - Ident()
        else:
            logger.error("%s", f'unknown calling_back_code type: {m.callback_type}')
            function_code = ''
        
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
    
    constants = r0.constants
    constants.update(r1.const_macros)
    
    functions = r0.functions
    classes = r1.classes
    
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
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    for name, data in saved_files.items():
        with open(f"{output_folder}/{name}", "wt") as f:
            f.write(data)


if __name__ == '__main__':
    main()
