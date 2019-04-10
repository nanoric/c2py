import logging
from dataclasses import dataclass
from typing import List

from autocxxpy.core.generator import GeneratorBase, GeneratorOptions, GeneratorResult
from autocxxpy.generator.cxxgenerator.utils import slugify
from autocxxpy.textholder import Indent, IndentLater, TextHolder
from autocxxpy.types.generator_types import CallingType, GeneratorClass, GeneratorEnum, \
    GeneratorFunction, GeneratorMethod, GeneratorNamespace, GeneratorSymbol

logger = logging.getLogger(__file__)


@dataclass()
class GeneratedFunction:
    name: str
    arg_type: str
    body: TextHolder


class IntermediateResult:

    def __init__(self):
        self.body: TextHolder = TextHolder()
        self.function_manager = FunctionManager()

    def extend(self, scope_handle_name: str, function_name: str, other: "IntermediateResult"):
        self.body += f"{function_name}({scope_handle_name})"
        self.function_manager.extend(other.function_manager)


class FunctionManager:
    """
    Manage generated cpp function.
    """

    def __init__(self):
        self.functions: List[GeneratedFunction] = []

    def add(self, name: str, arg_type: str, body: TextHolder):
        assert name not in self.functions, "Internal error."

        self.functions.append(GeneratedFunction(
            name, arg_type, body
        ))

    def extend(self, other: "FunctionManager"):
        self.functions.extend(other.functions)


@dataclass()
class CxxGeneratorOptions(GeneratorOptions):
    arithmetic_enum: bool = True
    max_lines_per_file: int = 30000  # 30k lines per file
    constants_in_class: str = "constants"
    caster_class_name: str = "caster"


class CxxGenerator(GeneratorBase):

    def __init__(self, options: CxxGeneratorOptions):
        super().__init__(options)
        self.options = options
        self.objects = options.objects

        self.function_manager = FunctionManager()

    def _process(self):

        # all classes
        self._output_wrappers()
        self._output_module()
        self._output_generated_functions()

        self._save_template(
            'module.hpp',
            module_tag=self.module_tag,
        )

    def _output_module(self):
        function_name = slugify(f'generate_{self.module_name}')
        function_body, fm = self._generate_namespace_body(self.options.g)

        module_body = TextHolder()
        module_body += 1
        module_body += f'{function_name}(m);'
        self._save_template(
            "module.cpp",
            "module.cpp",
            module_body=module_body,
            module_tag=self.module_tag,
        )
        self.function_manager.add(function_name, "pybind11::module &", function_body)
        self.function_manager.extend(fm)

    def _output_generated_functions(self):
        """
        :return:  # of files named 'generated_functions_??.cpp generated
        """
        # declaration
        decls = TextHolder()
        for f in self.function_manager.functions:
            decls += f'void {f.name}({f.arg_type} parent);'
        self._save_template('generated_functions.h',
                            'generated_functions.h',
                            includes=self._generate_includes(),
                            declarations=decls)

        # definitions
        total_lines = 0
        for f in self.function_manager.functions:
            total_lines += f.body.line_count

        prefer_lines_per_file = self.options.max_lines_per_file
        if total_lines > self.options.max_lines_per_file:
            prefer_lines_per_file = total_lines / int(total_lines / self.options.max_lines_per_file)

        defs = TextHolder()
        i = 0
        for f in self.function_manager.functions:
            defs += f'void {f.name}({f.arg_type} parent)'
            defs += "{" + Indent()
            defs += f.body
            defs += "}" - Indent()
            if defs.line_count >= prefer_lines_per_file:
                self._save_template(
                    'generated_functions.cpp',
                    f'generated_functions_{i}.cpp',
                    includes=self._generate_includes(),
                    definitions=defs,
                )
                defs = TextHolder()
                i += 1
        if len(str(defs)):
            self._save_template(
                'generated_functions.cpp',
                f'generated_functions_{i}.cpp',
                includes=self._generate_includes(),
                definitions=defs,
            )
        return i + 1  # return the number of generated_functions_.cpp generated

    def _output_wrappers(self):
        wrappers = ""
        # generate callback wrappers
        for c in self.objects.values():
            if (isinstance(c, GeneratorClass)
                and self._should_generate_symbol(c)
                and self._has_wrapper(c)
            ):
                py_class_name = "Py" + c.name
                wrapper_code = TextHolder()
                for ms in c.functions.values():
                    for m in ms:
                        if self._should_generate_symbol(m):
                            if m.is_virtual and not m.is_final:
                                function_code = self._generate_callback_wrapper(
                                    m,
                                )
                                wrapper_code += Indent(function_code)
                py_class_code = self._render_file(
                    "wrapper_class.h",
                    py_class_name=py_class_name,
                    class_fullname=c.full_name,
                    body=wrapper_code
                )
                wrappers += py_class_code
        self._save_template(f"wrappers.hpp", wrappers=wrappers)

    def _generate_class_body(self, c: GeneratorClass):
        body = TextHolder()
        fm = FunctionManager()
        class_name = c.full_name

        my_variable = "c"
        if self._has_wrapper(c):
            wrapper_class_name = "Py" + c.name
            if (
                c.destructor is None or
                c.destructor.access == "public"
            ):
                body += f"""pybind11::class_<{class_name}, {wrapper_class_name}> {my_variable}(parent, "{class_name}");\n"""
            else:
                body += f"pybind11::class_<" + Indent()
                body += f"{class_name},"
                body += f"std::unique_ptr<{class_name}, pybind11::nodelete>,"
                body += f"{wrapper_class_name}"
                body += (
                    f"""> {my_variable}(parent, "{class_name}");\n""" - Indent()
                )
        else:
            body += f"""pybind11::class_<{class_name}> {my_variable}(parent, "{class_name}");\n"""

        # constructor
        if not c.is_pure_virtual:
            if c.constructors:
                arg_list = ""
                for con in c.constructors:
                    arg_list = ",".join([arg.type for arg in con.args])

                comma = ',' if arg_list else ''
                body += f"""if constexpr (std::is_constructible_v<""" + Indent()
                body += f"""{class_name}{comma}{arg_list}"""
                body += f""">)""" - Indent()
                body += Indent(
                    f"""{my_variable}.def(pybind11::init<{arg_list}>());\n"""
                )
            else:
                body += f"""if constexpr (std::is_default_constructible_v<{class_name}>)"""
                body += Indent(f"""{my_variable}.def(pybind11::init<>());\n""")

        self._process_class_functions(c, body, my_variable)
        self._process_class_variables(ns=c,
                                      body=body,
                                      cpp_scope_variable=my_variable,
                                      pfm=fm)
        self._process_enums(ns=c,
                            body=body,
                            cpp_scope_variable=my_variable,
                            pfm=fm)
        self._process_classes(ns=c,
                              body=body,
                              cpp_scope_variable=my_variable,
                              pfm=fm)

        # post_register
        body += f'AUTOCXXPY_POST_REGISTER_CLASS({self.module_tag}, {class_name}, {my_variable});\n'

        # objects record
        body += f'{self.module_class}::objects.emplace("{c.full_name}", {my_variable});'

        return body, fm

    def _process_class_functions(self, c: GeneratorClass, body: TextHolder, my_variable: str):
        # functions
        for ms in c.functions.values():
            has_overload: bool = False
            if len(ms) > 1:
                has_overload = True
            for m in ms:
                if self._should_generate_symbol(m):
                    if m.is_static:
                        body += (
                            f"""{my_variable}.def_static("{m.alias}",""" + Indent()
                        )
                    else:
                        body += (
                            f"""{my_variable}.def("{m.alias}",""" + Indent()
                        )
                    body += self._generate_calling_wrapper(m, has_overload, append=',')
                    body += f"pybind11::call_guard<pybind11::gil_scoped_release>()"
                    body += f""");\n""" - Indent()

    def _process_namespace_functions(self, ns: GeneratorNamespace, cpp_scope_variable: str,
                                     body: TextHolder, pfm: FunctionManager):
        if ns.functions:
            for fs in ns.functions.values():
                for f in fs:
                    if self._should_generate_symbol(f):
                        has_overload: bool = False
                        if len(fs) > 1:
                            has_overload = True
                        for m in fs:
                            body += (
                                f"""{cpp_scope_variable}.def("{m.alias}",""" + Indent()
                            )
                            body += self._generate_calling_wrapper(f, has_overload, append=',')
                            body += f"pybind11::call_guard<pybind11::gil_scoped_release>()"
                            body += f""");\n""" - Indent()

    def _generate_enum_body(self, e: GeneratorEnum):
        fm = FunctionManager()
        body = TextHolder()

        my_variable = "e"
        if self.options.arithmetic_enum:
            arithmetic_enum_code = ", pybind11::arithmetic()"
        else:
            arithmetic_enum_code = ""
        body += (
            f'pybind11::enum_<{e.full_name}> {my_variable}(parent, "{e.alias}"{arithmetic_enum_code});'
        )

        for v in e.values.values():
            body += f'{my_variable}.value("{v.alias}", {v.full_name});'
        if not e.is_strong_typed:
            body += f'{my_variable}.export_values();'

        # objects record
        body += f'{self.module_class}::objects.emplace("{e.full_name}", {my_variable});'
        return body, fm

    def _process_enums(self, ns: GeneratorNamespace, body: TextHolder, cpp_scope_variable: str,
                       pfm: FunctionManager):
        if ns.enums:
            for e in ns.enums.values():
                if self._should_generate_symbol(e):
                    function_name = slugify(f"generate_enum_{e.full_name}")
                    function_body, fm = self._generate_enum_body(e)
                    body += f'{function_name}({cpp_scope_variable});'
                    # todo: generate alias ...

                    pfm.add(function_name, "pybind11::object &", function_body)
                    pfm.extend(fm)

    def _process_classes(self, ns: GeneratorNamespace, cpp_scope_variable: str, body: TextHolder,
                         pfm: FunctionManager):
        if ns.classes:
            for c in ns.classes.values():
                if self._should_generate_symbol(c):
                    function_name = slugify(f"generate_class_{c.full_name}")
                    function_body, fm = self._generate_class_body(c)
                    body += f'{function_name}({cpp_scope_variable});'
                    # todo: generate alias ...

                    pfm.add(function_name, "pybind11::object &", function_body)
                    pfm.extend(fm)

    def _process_class_variables(self, ns: GeneratorNamespace, cpp_scope_variable: str,
                                 body: TextHolder,
                                 pfm: FunctionManager):
        for value in ns.variables.values():
            body += f"""{cpp_scope_variable}.AUTOCXXPY_DEF_PROPERTY({self.module_tag}, {ns.full_name}, "{value.alias}", {value.name});\n"""

    def _process_namespace_variables(self, ns: GeneratorNamespace, cpp_scope_variable: str,
                                     body: TextHolder,
                                     pfm: FunctionManager):
        for value in ns.variables.values():
            if self._should_generate_symbol(value):
                body += f"""{cpp_scope_variable}.attr("{value.alias}") = {value.full_name};\n"""

    def _process_sub_namespace(self, ns: GeneratorNamespace, cpp_scope_variable: str,
                               body: TextHolder, pfm: FunctionManager):
        for n in ns.namespaces.values():
            assert n.name, "sub Namespace has no name, someting wrong in Parser or preprocessor"
            if self._should_generate_symbol(n):
                function_name = slugify(f"generate_sub_namespace_{n.full_name}")
                function_body, fm = self._generate_namespace_body(n)
                body += f'{function_name}({cpp_scope_variable});'
                # todo: generate alias (namespace alias)

                pfm.add(function_name, "pybind11::module &", function_body)
                pfm.extend(fm)

    def _process_typedefs(self, ns: GeneratorNamespace, cpp_scope_variable: str, body: TextHolder,
                          pfm: FunctionManager):
        for tp in ns.typedefs.values():
            if self._should_generate_symbol(tp):
                target = tp.target
                if target in self.objects and isinstance(self.objects[target], GeneratorClass):
                    body += f'{self.module_class}::cross.record_assign({cpp_scope_variable}, "{tp.name}", "{tp.full_name}", "{target}");'

    def _generate_caster_body(self, ns: GeneratorNamespace):
        fm = FunctionManager()
        body = TextHolder()
        cpp_scope_variable = "c"
        body += f"""auto {cpp_scope_variable} = autocxxpy::caster::bind(parent, "{self.options.caster_class_name}"); """
        for c in ns.classes.values():
            if self._should_generate_symbol(c):
                body += f'autocxxpy::caster::try_generate<{c.full_name}>({cpp_scope_variable}, "to{c.name})");'
        for p in ns.typedefs.values():
            if self._should_generate_symbol(p):
                body += f'autocxxpy::caster::try_generate<{p.full_name}>({cpp_scope_variable}, "to{p.name})");'

        return body, fm

    def _process_caster(self, ns: GeneratorNamespace, cpp_scope_variable: str, body: TextHolder,
                        pfm: FunctionManager):
        if self.options.caster_class_name:
            function_name = slugify(f"generate_caster_{ns.full_name}")
            function_body, fm = self._generate_caster_body(ns)
            body += f'{function_name}({cpp_scope_variable});'

            pfm.add(function_name, "pybind11::object &", function_body)
            pfm.extend(fm)

    def _generate_namespace_body(self, ns: GeneratorNamespace):
        fm = FunctionManager()
        body = TextHolder()
        cpp_scope_variable = "parent"

        self._process_sub_namespace(ns=ns, cpp_scope_variable=cpp_scope_variable, body=body, pfm=fm)
        self._process_classes(ns=ns, cpp_scope_variable=cpp_scope_variable, body=body, pfm=fm)
        self._process_enums(ns=ns, cpp_scope_variable=cpp_scope_variable, body=body, pfm=fm)
        self._process_namespace_functions(ns=ns, cpp_scope_variable=cpp_scope_variable, body=body,
                                          pfm=fm)
        self._process_namespace_variables(ns=ns, cpp_scope_variable=cpp_scope_variable, body=body,
                                          pfm=fm)
        self._process_typedefs(ns=ns, cpp_scope_variable=cpp_scope_variable, body=body, pfm=fm)

        self._process_caster(ns=ns, cpp_scope_variable=cpp_scope_variable, body=body, pfm=fm)

        return body, fm

    @staticmethod
    def _generate_calling_wrapper(m: GeneratorFunction, has_overload, append=''):
        code = TextHolder()
        code += f'autocxxpy::apply_function_transform<' + Indent()
        code += f'autocxxpy::function_constant<' + Indent()

        if has_overload:
            code += f'static_cast<{m.type}>(' + Indent()
        code += f"""&{m.full_name}"""
        if has_overload:
            code += f""")""" - IndentLater()

        code += '>, ' - Indent()

        code += 'brigand::list<' + Indent()
        lines = [f'autocxxpy::indexed_transform_holder<autocxxpy::{wi.wrapper.name}, {wi.index}>'
                 for wi in m.wrappers]
        code.append_lines(lines, ',')
        code += '>' - Indent()

        code += f'>::value{append}' - Indent()
        return code

    def _generate_callback_wrapper(
        self, m: GeneratorMethod,
    ):
        # calling_back_code
        ret_type = m.ret_type
        args = m.args
        arguments_signature = ",".join([f"{i.type} {i.name}" for i in args])
        arg_list = ",".join(
            ["this", f'"{m.alias}"', *[f"{i.name}" for i in args]]
        )

        if m.has_overload:
            cast_expression = f"static_cast<{m.type}>(&{m.full_name})"
        else:
            cast_expression = f"&{m.full_name}"

        function_code = TextHolder()
        function_code += (
            f"{ret_type} {m.name}({arguments_signature}) override\n"
        )
        function_code += "{\n" + Indent()
        calling_method = "call"
        if m.calling_type == CallingType.Async:
            calling_method = "async"
        elif m.calling_type == CallingType.Sync:
            calling_method = "sync"

        function_code += (
            f"return autocxxpy::callback_wrapper<{cast_expression}>::{calling_method}("
            + Indent()
        )
        function_code += f"{arg_list}" - IndentLater()
        function_code += f");"
        function_code += "}\n" - Indent()

        return function_code

    def _has_wrapper(self, c: GeneratorClass):
        return c.is_polymorphic

    def _should_generate_symbol(self, s: GeneratorSymbol):
        return s.generate and s.name
