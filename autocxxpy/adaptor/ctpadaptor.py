import logging
import os
from typing import List

from autocxxpy.parser.cxxparser import CXXFileParser, CXXParseResult
from autocxxpy.generator import GeneratorOptions
from autocxxpy.generator.preprocessor import PreProcessor, PreProcessorOptions, PreProcessorResult

logger = logging.getLogger(__file__)


def clear_dir(path: str):
    for file in os.listdir(path):
        os.unlink(os.path.join(path, file))


class CtpAdaptor:

    def __init__(self, headers: List[str], include_paths: List[str]):
        self.include_paths = include_paths
        self.headers = headers

    def parse(self) -> GeneratorOptions:
        r0: CXXParseResult = CXXFileParser(
            files=self.headers,
            include_paths=self.include_paths
        ).parse()

        pre_processor_options = PreProcessorOptions(parse_result=r0, )
        r1: PreProcessorResult = PreProcessor(pre_processor_options).process()

        variables = r0.variables
        variables.update(r1.const_macros)
        variables = {
            k: v for k, v in variables.items() if not k.startswith("_")
        }

        functions = r1.functions
        classes = r1.classes
        enums = r1.enums

        # make all api "final" to improve performance
        for c in classes.values():
            type = c.name[-3:]
            if type == "Api":
                for ms in c.functions.values():
                    for m in ms:
                        if m.is_virtual:
                            m.is_pure_virtual = False
                            m.is_final = True
            elif type == "Spi":
                for ms in c.functions.values():
                    for m in ms:
                        m.is_virtual = True
                        # m.is_pure_virtual = True
                        m.is_final = False

        options = GeneratorOptions(
            typedefs=r1.typedefs,
            variables=variables,
            functions=functions,
            classes=classes,
            dict_classes=r1.dict_classes,
            enums=enums,

            split_in_files=True,
            max_classes_in_one_file=80,
        )
        options.include_files.extend(self.headers)
        return options
