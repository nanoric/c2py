import logging
from dataclasses import dataclass

from autocxxpy.core.generator import GeneratorBase, GeneratorOptions
from autocxxpy.textholder import Indent, TextHolder
from autocxxpy.type_manager import TypeManager
from autocxxpy.types.generator_types import GeneratorClass, GeneratorNamespace, GeneratorSymbol, \
    GeneratorVariable

logger = logging.getLogger(__file__)


@dataclass()
class PyiGeneratorOptions(GeneratorOptions):
    pass


class PyiGenerator(GeneratorBase):

    def __init__(self, options: PyiGeneratorOptions):
        super().__init__(options)
        self.options = options
        self.objects = options.g.objects

        self.type_manager = TypeManager(self.options.g)

    def _process(self):
        code = self._process_namespace(self.options.g)
        self._save_template(
            "hint.py.in",
            f'{self.module_name}.pyi',
            hint_code=code,
        )

    def _process_class(self, c: GeneratorClass):
        code = TextHolder()

        parent_place = f'({c.parent.name})'
        code += f'class {c.name}{parent_place}:' + Indent()
        for v in c.variables.values():
            if not self._should_generate_symbol(v):
                continue
            code += self._variable_with_hint(v)
        return code

    def _process_variable(self, v):
        return self._variable_with_hint(v)

    def _process_namespace(self, ns: GeneratorNamespace):
        code = TextHolder()

        for c in ns.classes.values():
            code += self._process_class(c)
        for v in ns.variables.values():
            code += self._process_variable(v)
        return code

    def _variable_with_hint(self, v: GeneratorVariable, comment: str = ''):
        python_type = self.type_manager.cpp_type_to_python(v.type)
        comment_place = f'# {comment}'
        return f'{v.name}: {python_type}  {comment_place}'

    def _should_generate_symbol(self, c: GeneratorSymbol):
        return c.generate and c.name
