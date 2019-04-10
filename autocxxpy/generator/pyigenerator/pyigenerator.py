import logging
from dataclasses import dataclass
from typing import Callable, Union

from autocxxpy.core.generator import GeneratorBase, GeneratorOptions
from autocxxpy.textholder import Indent, TextHolder
from autocxxpy.type_manager import TypeManager
from autocxxpy.types.generator_types import GeneratorClass, GeneratorEnum, GeneratorNamespace, \
    GeneratorSymbol, GeneratorVariable, filter_recursive, GeneratorTypedef

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
        global_namespace = filter_recursive(
            v=self.options.g,
            symbol_filter=self._should_generate_symbol
        )
        # global_namespace = self.options.g
        code = self._process_namespace(global_namespace)
        self._save_template(
            "hint.py.in",
            f'{self.module_name}.pyi',
            hint_code=code,
        )

    def _process_class(self, c: GeneratorClass):
        code = TextHolder()

        # parent_place = f'({c.parent.name})' if c.parent and c.parent.name else ''
        parent_place = f'({c.parent.name})'
        code += f'class {c.name}{parent_place}:' + Indent()
        code += self._process_typedefs(c)
        code += self._process_classes(c)
        code += self._process_variables(c)
        code += self._process_enums(c)
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

    def _process_typedefs(self, ns: GeneratorNamespace):
        return self.batch_process(ns, "typedefs", self._process_typedef)

    def _process_variables(self, ns: Union[GeneratorNamespace, GeneratorEnum]):
        return self.batch_process(ns, "variables", self._process_variable)

    def _process_classes(self, ns: GeneratorNamespace):
        return self.batch_process(ns, "classes", self._process_class)

    def _process_enums(self, ns: GeneratorNamespace):
        return self.batch_process(ns, "enums", self._process_enum)

    def batch_process(self, ns: GeneratorNamespace, attr_name: str, func: Callable):
        code = TextHolder()
        for v in getattr(ns, attr_name).values():
            code += func(v)
        return code

    def _process_namespace(self, ns: GeneratorNamespace):
        code = TextHolder()

        code += self._process_classes(ns)
        code += self._process_enums(ns)
        code += self._process_typedefs(ns)
        code += self._process_variables(ns)
        return code

    def _variable_with_hint(self, v: GeneratorVariable, comment: str = ''):
        python_type = self.type_manager.cpp_type_to_python(v.type)
        comment_place = f'# {comment}'
        return f'{v.name}: {python_type}  {comment_place}'

    @staticmethod
    def _should_generate_symbol(c: GeneratorSymbol):
        return c.generate and c.name
