import logging
import os

from autocxxpy.adaptor.ctpadaptor import CtpAdaptor
from autocxxpy.generator import Generator, GeneratorOptions

logger = logging.getLogger(__file__)

include_root = "vnlts/include"


def clear_dir(path: str):
    for file in os.listdir(path):
        os.unlink(os.path.join(path, file))


def main():
    options: GeneratorOptions = CtpAdaptor(
        [
            "lts/SecurityFtdcMdApi.h",
            "lts/SecurityFtdcQueryApi.h",
            "lts/SecurityFtdcTraderApi.h",
            "lts/SecurityFtdcUserApiDataType.h",
            "lts/SecurityFtdcUserApiStruct.h",
        ],
        include_paths=[include_root],
    ).parse()

    options.split_in_files = True
    options.module_name = "vnlts"
    options.max_classes_in_one_file = 75
    options.include_files.append("custom/custom_wrappers.hpp")

    saved_files = Generator(options=options).generate()
    output_dir = "./vnlts/generated_files"
    # clear output dir
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    clear_dir(output_dir)

    for name, data in saved_files.items():
        with open(f"{output_dir}/{name}", "wt") as f:
            f.write(data)


if __name__ == "__main__":
    main()
