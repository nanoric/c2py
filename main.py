import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from TextHolder import Ident, TextHolder
from cxxparser import CXXParser, Function, Variable
from preprocessor import CallbackType, PreProcessor, PreprocessedClass
from type import _is_pointer_type, remove_cvref

logger = logging.getLogger(__file__)


def _read_file(name: str):
    with open(name, "rt") as f:
        return f.read()


def render_template(template: str, **kwargs):
    for key, replacement in kwargs.items():
        template = template.replace(f"${key}", str(replacement))
    return template


def default_includes():
    return []


@dataclass
class GeneratorOptions:
    constants: Dict[str, Any]  # to global value
    functions: Dict[str, Function]  # to def
    classes: Dict[str, PreprocessedClass]  # to class
    dict_classes: Set[str]  # to dict
    includes: List[str] = field(default_factory=default_includes)
    split_in_files: bool = True
    module_name: str = 'vnctptd'


class Generator:

    def __init__(self, options: GeneratorOptions):
        self.options = options

        self.template_dir = "templates"

        self.saved_files = {'helper.h': _read_file(f'{self.template_dir}/helper.h')}

    def generate(self):

        # all classes
        self._output_wrappers()
        self._output_module()
        self._output_class_declarations()

        return self.saved_files

    def _output_wrappers(self):
        wrapper_template = _read_file(f'{self.template_dir}/wrapper.h')
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
        wrapper_code = self.render_template(wrapper_template, wrappers=wrappers)
        self._save_file(f'wrapper.h', wrapper_code)

    def _output_class_declarations(self):
        class_generator_header_template = _read_file(f'{self.template_dir}/class_generators.h')

        class_generator_declarations = TextHolder()
        for c in self.options.classes.values():
            class_name = c.name
            if c.name not in self.options.dict_classes:
                class_generator_function_name = self._generate_class_generator_function_name(
                    class_name)
                class_generator_declarations += f"void {class_generator_function_name}(pybind11::module &m);"

        class_generator_header_code = self.render_template(
            class_generator_header_template,
            class_generator_declarations=class_generator_declarations,
        )
        self._save_file(f'class_generators.h', class_generator_header_code)

    def _output_module(self):
        module_template = _read_file(f'{self.template_dir}/module.cpp')
        class_template = _read_file(f'{self.template_dir}/class.cpp')
        module_body = TextHolder()
        classes_generator_definitions = TextHolder()
        # generate class module_body
        for c in self.options.classes.values():
            class_name = c.name
            if c.name not in self.options.dict_classes:
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
                    class_code = self.render_template(
                        class_template,
                        class_generator_definition=class_generator_code,
                    )
                    self._save_file(f'{class_name}.cpp', class_code)
                else:
                    classes_generator_definitions += class_generator_code

                module_code = TextHolder()
                module_code += f"{class_generator_function_name}(m);"
                module_body += Ident(module_code)
        class_code = self.render_template(
            module_template,
            classes_generator_definitions=classes_generator_definitions,
            module_body=module_body,
        )
        self._save_file(f'{self.options.module_name}.cpp', class_code)

    def _generate_class_generator_function_name(self, class_name):
        class_generator_function_name = f"generate_class_{class_name}"
        return class_generator_function_name

    def _has_wrapper(self, c: PreprocessedClass):
        return c.name not in self.options.dict_classes and c.is_polymorphic

    def _method_dict_types(self, m):
        # filter all arguments can convert as dict
        arg_base_types = set(remove_cvref(i.type) for i in m.args.values())
        return arg_base_types & self.options.dict_classes

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
                ('&' if _is_pointer_type(i.type) else '') + (i.name if i.type not in dict_types else "py" + i.name)
                                     for i in deref_args])

            fucking const
            calling_back_code += f"""{convert_code}"""
            calling_back_code += f"""{overload_symbol}({m.ret_type}, {c.name}, {m.name}, {forward_args});\n"""
        else:
            forward_args = ",".join([
                (f'std::remove_const_t<decltype(_pCancelAccount)>(&{i.name})' if _is_pointer_type(i.type) else i.name) for i in deref_args])
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
    for name, data in saved_files.items():
        with open(f"{output_folder}/{name}", "wt") as f:
            f.write(data)


if __name__ == '__main__':
    main()
