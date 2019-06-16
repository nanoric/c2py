import logging
from dataclasses import dataclass
from typing import List

from autocxxpy.core.generator import BasicGeneratorOption, GeneratorBase, GeneratorResult

logger = logging.getLogger(__file__)


@dataclass()
class SetupGeneratorOptions(BasicGeneratorOption):
    output_dir: str = ""
    include_dirs: List[str] = None
    lib_dirs: List[str] = None
    libs: List[str] = None
    cxx_result: GeneratorResult = None
    use_patches: bool = False


class SetupGenerator(GeneratorBase):

    def __init__(self, options: SetupGeneratorOptions):
        super().__init__(options)
        self.options = options

    def _get_patches(self):
        return self._template_content("setup_patches.py.in")

    def _process(self):
        options = self.options
        result = options.cxx_result.saved_files
        self._save_template(
            "setup.py.in",
            'setup.py',
            version='1.0.0',
            sources=list(result.keys()),
            source_root=options.output_dir,
            include_dirs=repr(options.include_dirs),
            library_dirs=repr(options.lib_dirs),
            libraries=repr(options.libs),
            patches=self._get_patches() if options.use_patches else '',
        )
