import logging
import os

from autocxxpy.cxxparser import CXXFileParser, CXXParseResult
from autocxxpy.generator import Generator, GeneratorOptions
from autocxxpy.preprocessor import PreProcessor, PreProcessorOptions, PreProcessorResult
from autocxxpy.type import remove_cvref

logger = logging.getLogger(__file__)

oes_root = "oes_libs-0.15.7.4-release\\include"


def clear_dir(path: str):
    for file in os.listdir(path):
        os.unlink(os.path.join(path, file))


def main():
    includes = [
        'oes_api/oes_api.h',
        'mds_api/mds_api.h',
        'mds_api/parser/json_parser/mds_json_parser.h',
    ]

    r0: CXXParseResult = CXXFileParser(
        [
            *includes,
            "vnoes/helper.hpp"
        ],
        include_paths=[oes_root],
    ).parse()
    r1: PreProcessorResult = PreProcessor(PreProcessorOptions(r0)).process()

    constants = r0.variables
    constants.update(r1.const_macros)
    constants = {
        k: v for k, v in constants.items() if not k.startswith("_")
    }

    functions = r1.functions
    classes = r1.classes
    enums = r1.enums

    # ignore some ugly function
    functions.pop('OesApi_SendBatchOrdersReq')
    functions.pop('MdsApi_SubscribeByString2')
    functions.pop('MdsApi_SubscribeByStringAndPrefixes2')

    # fix unrecognized std::unique_ptr
    for c in classes.values():
        if c.name == 'helper':
            for ms in c.functions.values():
                for m in ms:
                    if m.name.startswith('to') and remove_cvref(m.ret_type) == 'int':
                        m.ret_type = m.name[2:]

    #OesApi_WaitReportMsg
    #MdsApi_WaitOnTcpChannelGroup

    options = GeneratorOptions(
        typedefs=r0.typedefs,
        constants=constants,
        functions=functions,
        classes=classes,
        dict_classes=r1.dict_classes,
        enums=enums,
    )
    options.includes.extend(includes)
    options.includes.append("custom/wrapper.hpp")
    options.includes.append("custom/init.hpp")
    options.includes.append("helper.hpp")

    options.split_in_files = True
    options.module_name = "vnoes"
    options.max_classes_in_one_file = 100

    saved_files = Generator(options=options).generate()
    output_dir = "vnoes/generated_files"
    # clear output dir
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    clear_dir(output_dir)

    for name, data in saved_files.items():
        with open(f"{output_dir}/{name}", "wt") as f:
            f.write(data)


if __name__ == "__main__":
    main()
