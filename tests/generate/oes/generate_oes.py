import logging
import os

from autocxxpy.cxxparser import CXXParseResult, CXXFileParser
from autocxxpy.generator import GeneratorOptions, Generator
from autocxxpy.preprocessor import PreProcessor, PreProcessorResult

logger = logging.getLogger(__file__)

oes_root = "oes_libs-0.15.7.4-release\\include"


def clear_dir(path: str):
    for file in os.listdir(path):
        os.unlink(os.path.join(path, file))


def main():
    oes_api_file = os.path.join(oes_root, "oes_api", "oes_api.h")
    r0: CXXParseResult = CXXFileParser(
        [
            oes_api_file
        ],
        include_paths=[oes_root],
    ).parse()
    r1: PreProcessorResult = PreProcessor(r0).process()

    constants = r0.variables
    constants.update(r1.const_macros)
    constants = {
        k: v for k, v in constants.items() if not k.startswith("_")
    }

    functions = r0.functions
    classes = r1.classes

    options = GeneratorOptions(
        typedefs=r0.typedefs,
        constants=constants,
        functions=functions,
        classes=classes,
        dict_classes=r1.dict_classes,
        enums=r0.enums,
    )
    options.includes.append("oes_api/oes_api.h")
    options.split_in_files = True
    options.module_name = "vnoes"
    options.max_classes_in_one_file = 100

    saved_files = Generator(options=options).generate()
    output_dir = "./generated_files"
    # clear output dir
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    clear_dir(output_dir)

    for name, data in saved_files.items():
        with open(f"{output_dir}/{name}", "wt") as f:
            f.write(data)


if __name__ == "__main__":
    main()
