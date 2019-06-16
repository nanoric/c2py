import logging
from dataclasses import dataclass
from typing import Callable, Union

from autocxxpy.core.generator import GeneratorBase, GeneratorOptions
from autocxxpy.textholder import Indent, TextHolder
from autocxxpy.type_manager import TypeManager, is_tuple_type
from autocxxpy.core.core_types.generator_types import GeneratorClass, GeneratorEnum, GeneratorNamespace, \
    GeneratorSymbol, GeneratorVariable, GeneratorTypedef, GeneratorFunction, GeneratorMethod

logger = logging.getLogger(__file__)


@dataclass()
class PyiGeneratorOptions(GeneratorOptions):
    pass


class PyiGenerator(GeneratorBase):

    def __init__(self, options: PyiGeneratorOptions):
        super().__init__(options)
        self.options = options
        self.objects = options.objects

        self.type_manager = TypeManager(self.options.g, self.objects)

    def _process(self):
        self._process_namespace(self.options.g)

    def _process_class(self, c: GeneratorClass):
        code = TextHolder()

        # parent_place = f'({c.parent.name})' if c.parent and c.parent.name else ''
        super_list = ",".join([self._to_python_type(i.full_name) for i in c.super])
        parent_place = f'({super_list})'
        code += f'class {c.name}{parent_place}:' + Indent()
        code += self._process_typedefs(c)
        code += self._process_classes(c)
        code += self._process_variables(c)
        code += self._process_enums(c)
        code += self._process_methods(c)
        return code

    def _process_variable(self, v):
        return self._variable_with_hint(v)

    def _process_enum(self, e: GeneratorEnum):
        code = TextHolder()
        code += f'class {e.name}(Enum):' + Indent()
        code += self._process_variables(e)
        return code

    def _process_typedef(self, t: GeneratorTypedef):
        target = t.target
        target = self.type_manager.cpp_type_to_python(target)
        python_full_name = target.replace("::", ".")
        python_full_name = python_full_name.strip('.')
        return f'{t.name} = {python_full_name}'

    def _return_description_for_function(self, of: GeneratorFunction):
        code = TextHolder()
        return_elements = ['"retv"', ]
        wf = of
        for wi in wf.wrappers:
            arg = wf.args[wi.index]
            return_elements.append(f'"{arg.name}"')
            wf = wi.wrapper.wrap(f=wf, index=wi.index, wrapper_info=wi)
        return_str = ",".join(return_elements)
        code += f'return {return_str}'
        return code

    def _process_method(self, of: GeneratorMethod):
        wf = of.resolve_wrappers()
        code = TextHolder()
        arg_decls = ", ".join([self._variable_with_hint(i) for i in wf.args])

        self_text = 'self, '
        if wf.is_static:
            code += "@staticmethod"
            self_text = ""
        if wf.has_overload:
            code += "@overload"

        code += f'def {wf.name}({self_text}{arg_decls})->{self._to_python_type(wf.ret_type)}:'
        if is_tuple_type(wf.ret_type):
            code += Indent(self._return_description_for_function(of))
        else:
            code += Indent("...")
        return code

    def _process_function(self, of: GeneratorFunction):
        wf = of.resolve_wrappers()
        code = TextHolder()
        arg_decls = ", ".join([self._variable_with_hint(i) for i in wf.args])
        code += f'def {wf.name}({arg_decls})->{self._to_python_type(wf.ret_type)}:'
        if is_tuple_type(wf.ret_type):
            code += Indent(self._return_description_for_function(of))
        else:
            code += Indent("...")
        return code

    def _process_typedefs(self, ns: GeneratorNamespace):
        return self.batch_process(ns, "typedefs", self._process_typedef)

    def _process_variables(self, ns: Union[GeneratorNamespace, GeneratorEnum]):
        return self.batch_process(ns, "variables", self._process_variable)

    def _process_classes(self, ns: GeneratorNamespace):
        return self.batch_process(ns, "classes", self._process_class)

    def _process_enums(self, ns: GeneratorNamespace):
        return self.batch_process(ns, "enums", self._process_enum)

    def _process_methods(self, ns: GeneratorClass):
        code = TextHolder()
        for ms in ns.functions.values():
            for m in ms:
                code += self._process_method(m)
        return code

    def _process_functions(self, ns: GeneratorNamespace):
        code = TextHolder()
        for ms in ns.functions.values():
            for m in ms:
                code += self._process_function(m)
        return code

    def _process_namespaces(self, ns: GeneratorNamespace):
        code = TextHolder()
        for n in ns.namespaces.values():
            code += self._process_namespace(n)
        return code

    def batch_process(self, ns: GeneratorNamespace, attr_name: str, func: Callable):
        code = TextHolder()
        container: dict = getattr(ns, attr_name)
        for v in container.values():
            code += func(v)
        return code

    def _process_namespace(self, ns: GeneratorNamespace):
        code = TextHolder()

        # import sub modules first
        code_filename_base = self._module_filename_base(ns)

        code += self._process_namespaces(ns)
        code += self._process_classes(ns)
        code += self._process_enums(ns)
        code += self._process_typedefs(ns)
        code += self._process_variables(ns)
        code += self._process_functions(ns)

        self._save_template(
            "hint.py.in",
            f'{code_filename_base}.pyi',
            hint_code=code,
        )

        return f"from . import {code_filename_base} as {ns.name}"

    def _module_filename_base(self, n: GeneratorNamespace):
        module = n.full_name.replace("::", "_")
        if not module:
            filename = f"{self.module_name}"
            # filename = "__init__"
        else:
            filename = f'{self.module_name}_{module}'
        return filename

    def _to_python_type(self, t: str):
        python_type = self.type_manager.cpp_type_to_python(t)
        return python_type

    def _variable_with_hint(self, v: GeneratorVariable, comment: str = ''):
        python_type = self._to_python_type(v.type)
        code = f'{v.name}: {python_type}'
        if comment:
            code += f'  # {comment}'
        return code

    @staticmethod
    def _should_generate_symbol(c: GeneratorSymbol):
        return c.generate and c.name
