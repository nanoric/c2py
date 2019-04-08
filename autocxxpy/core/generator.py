import logging
import os
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Sequence

from autocxxpy.core.preprocessor import PreProcessorResult
from autocxxpy.types.generator_types import GeneratorNamespace

logger = logging.getLogger(__file__)
mydir = os.path.split(os.path.abspath(__file__))[0]


def _read_file(name: str):
    with open(name, "rt") as f:
        return f.read()


def render_template(template: str, **kwargs):
    for key, replacement in kwargs.items():
        template = template.replace(f"${key}", str(replacement))
    return template


@dataclass(repr=False)
class GeneratorOptions:
    g: GeneratorNamespace
    module_name: str = "unknown_module"
    include_files: Sequence[str] = field(default_factory=list)

    @classmethod
    def from_preprocessor_result(
        cls,
        module_name: str,
        pre_process_result: PreProcessorResult,
        include_files: Sequence[str] = None,
    ):
        return cls(
            module_name=module_name,
            g=pre_process_result.g,
            include_files=include_files,
        )


@dataclass()
class GeneratorResult:
    saved_files: Dict[str, str] = None

    def output(self, output_dir: str, clear: bool = False):
        # clear output dir
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        if clear:
            self.clear_dir(output_dir)

        for name, data in self.saved_files.items():
            with open(f"{output_dir}/{name}", "wt") as f:
                f.write(data)

    @staticmethod
    def clear_dir(path: str):
        for file in os.listdir(path):
            os.unlink(os.path.join(path, file))

    def print_filenames(self):
        print(f"# of files generated : {len(self.saved_files)}")
        for name in self.saved_files:
            print(name)


class GeneratorBase:
    template_dir = os.path.join(mydir, "../", "templates")

    def __init__(self, options: GeneratorOptions):
        self.options = options
        self.saved_files: Dict[str, str] = {}

    @abstractmethod
    def generate(self):
        """
        :return: GeneratorResult
        """
        return GeneratorResult(self.saved_files)

    @property
    def module_name(self):
        return self.options.module_name

    @property
    def module_tag(self):
        return 'tag_' + self.options.module_name

    @property
    def module_class(self):
        return "module_" + self.options.module_name

    def _save_template(
        self, template_filename: str, output_filename: str = None, **kwargs
    ):
        template = _read_file(f"{self.template_dir}/{template_filename}")
        if output_filename is None:
            output_filename = template_filename
        return self._save_file(
            output_filename, self._render_template(template, **kwargs)
        )

    def _render_file(self, template_filename: str, **kwargs):
        template = _read_file(f"{self.template_dir}/{template_filename}")
        return self._render_template(template, **kwargs)

    def _save_file(self, filename: str, data: str):
        self.saved_files[filename] = data

    def _render_template(self, templates: str, **kwargs):
        kwargs["includes"] = self._generate_includes()
        kwargs["module_name"] = self.module_name
        kwargs["module_tag"] = self.module_tag
        kwargs["module_class"] = self.module_class
        return render_template(templates, **kwargs)

    def _generate_includes(self):
        code = ""
        for i in self.options.include_files:
            code += f"""#include "{i}"\n"""
        return code
