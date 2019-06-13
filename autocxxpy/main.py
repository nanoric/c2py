import os
import re
import shutil
from distutils.dir_util import copy_tree
from typing import Callable, List

import click

from autocxxpy.core import CxxFileParser
from autocxxpy.core.preprocessor import PreProcessor, PreProcessorOptions
from autocxxpy.core.types.generator_types import GeneratorMethod, GeneratorSymbol, GeneratorFunction
from autocxxpy.generator.cxxgenerator.cxxgenerator import CxxGenerator, CxxGeneratorOptions
from autocxxpy.generator.pyigenerator.pyigenerator import PyiGenerator
from autocxxpy.objects_manager import ObjectManager

my_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(my_dir, ".."))
autocxxpy_include_dir = os.path.join(my_dir, "include")
autocxxpy_include_dir = os.path.abspath(autocxxpy_include_dir)
third_party_include_dir = os.path.join(root_dir, "3rd_party", "include")
third_party_include_dir = os.path.abspath(third_party_include_dir)


@click.command(help="""
Converts c/c++ .h files into python module source files.
All matching is based on c++ qualified name, using regex.
""")
@click.argument("module-name",
                nargs=1
                )
@click.argument("files",
                type=click.Path(),
                nargs=-1
                )
@click.option(
    "-e", "--encoding",
    help="encoding of input files, default is utf-8",
    default='utf-8'
)
@click.option("-o", "--output-dir",
              help="module source output directory",
              type=click.Path(),
              nargs=1,
              default="generated_files",
              )
@click.option("-p", "--pyi-output-dir",
              help="pyi files output directory",
              type=click.Path(),
              nargs=1,
              default="{output_dir}/{module_name}",

              )
@click.option("-I", "--include-path", "include_dirs",
              help="additional include paths",
              multiple=True)
@click.option("-A", "--additional-include", "additional_includes",
              help="additional include files. These files will be included in output cxx file,"
                   " but skipped by parser.",
              multiple=True)
@click.option("-i", "--ignore-pattern",
              help="ignore symbols matched",
              )
@click.option("--no-callback-pattern",
              help="disable generation of callback for functions matched\n"
                   "(for some virtual method used as undocumented API)",
              )
@click.option("--no-transform-pattern",
              help="disable applying transforms(changing its signature) into functions matched\n"
                   "(for some virtual method used as callback only)",
              )
@click.option("--inout-arg-pattern",
              help="make symbol(arguments only) as input_output",
              )
@click.option("--output-arg-pattern",
              help="make symbol(arguments only) as output only",
              )
@click.option(
    "--m2c/--no-m2c",
    help="treat const macros as global variable",
    default=True
)
@click.option(
    "--ignore-underline-prefixed/--no-ignore-underline-prefixed",
    help="ignore global variables starts with underline"
)
@click.option(
    "--ignore-unsupported/--no-ignore-unsupported",
    help="ignore functions that has unsupported argument",
    default=True,
)
@click.option(
    "-m",
    "--max-lines-per-file",
    type=click.IntRange(min=200, clamp=True),
    default=500,
)
@click.option(
    "--clear-output/--no-clear-output",
    default=True,
)
@click.option(
    "--clear-pyi-output/--no-clear-pyi-output",
    default=True,
)
@click.option(
    "--copy-autocxxpy-includes",
    help="copy all autocxxpy include files, excluding input files to specific dir.",
    default="",
)
@click.option(
    "--string-encoding-windows",
    help="encoding used to get & set string. This value is used to construct std::locale.\n"
    "use `locale -a` to show all the locates supported.\n"
    "default is utf-8, which is the internal encoding used by pybind11.",
    default="utf-8",
)
@click.option(
    "--string-encoding-linux",
    help="encoding used to get & set string. This value is used to construct std::locale.\n"
         "use `locale -a` to show all the locates supported.\n"
         "default is utf-8, which is the internal encoding used by pybind11.",
    default="utf-8",
)
# @click.option(
#     "--char-macro-to-int/--no-char-macro-to-int",
#     help="enable this to converts char macros to int.(default imported as str).\n"
#     "char macros are macros like #define AAA 'ch' ",
#     default=False,
# )
def main(
    module_name: str,
    files: List[str],
    output_dir: str,
    pyi_output_dir: str,
    include_dirs: List[str],
    additional_includes: List[str],
    ignore_pattern: str,
    inout_arg_pattern: str,
    output_arg_pattern: str,
    no_callback_pattern: str,
    no_transform_pattern: str,
    m2c: bool,
    ignore_underline_prefixed: bool,
    ignore_unsupported: bool,
    max_lines_per_file: bool,
    encoding: str = 'utf-8',
    clear_output: bool = True,
    clear_pyi_output: bool = False,
    copy_autocxxpy_includes: str = "",
    string_encoding_windows: str = "utf-8",
    string_encoding_linux: str = "utf-8",
    # char_macro_to_int: bool = False
):
    local = locals()
    pyi_output_dir = pyi_output_dir.format(**local)
    print("parsing ...")
    parser = CxxFileParser(files=files, encoding=encoding, include_paths=include_dirs)
    parser_result = parser.parse()
    print("parse finished.")

    print()
    print("processing result ...")
    pre_processor_options = PreProcessorOptions(parser_result)
    pre_processor_options.treat_const_macros_as_variable = m2c
    pre_processor_options.ignore_global_variables_starts_with_underline = ignore_underline_prefixed
    pre_processor_options.ignore_unsupported_functions = ignore_unsupported
    pre_processor_options.inout_arg_pattern = re.compile(
        inout_arg_pattern) if inout_arg_pattern else None
    pre_processor_options.output_arg_pattern = re.compile(
        output_arg_pattern) if output_arg_pattern else None
    # pre_processor_options.char_macro_to_int = char_macro_to_int
    pre_processor_result = PreProcessor(pre_processor_options).process()
    print("process finished.")
    pre_processor_result.print_unsupported_functions()

    def apply_filter(objects: ObjectManager, pattern: str, callback: Callable[["GeneratorSymbol"], None]):
        if pattern:
            r = re.compile(pattern)
            for f in objects.values():  # type: GeneratorSymbol
                m = r.match(f.full_name)
                if m:
                    callback(f)

    def ignore_name(s: "GeneratorSymbol"):
        s.generate = False

    def disable_callback(s: "GeneratorSymbol"):
        if isinstance(s, GeneratorMethod):
            s.is_final = True

    def disable_transform(s: "GeneratorSymbol"):
        if isinstance(s, GeneratorFunction):
            s.wrappers.clear()

    apply_filter(pre_processor_result.objects, ignore_pattern, ignore_name)
    apply_filter(pre_processor_result.objects, no_callback_pattern, disable_callback)
    apply_filter(pre_processor_result.objects, no_transform_pattern, disable_transform)

    print()
    print("generating cxx code ...")
    options = CxxGeneratorOptions.from_preprocessor_result(
        module_name=module_name,
        pre_processor_result=pre_processor_result,
        include_files=[*files, *additional_includes],
    )

    options.max_lines_per_file = max_lines_per_file
    options.string_encoding_windows = string_encoding_windows
    options.string_encoding_linux = string_encoding_linux
    cxx_result = CxxGenerator(options=options).generate()
    print("cxx code generated.")

    print()
    print("generating pyi code ...")
    pyi_result = PyiGenerator(options=options).generate()
    print("pyi code generated.")

    cxx_result.print_filenames()
    cxx_result.output(output_dir=output_dir, clear=clear_output)

    pyi_result.output(output_dir=pyi_output_dir, clear=clear_pyi_output)
    pyi_result.print_filenames()

    if copy_autocxxpy_includes:
        copy_tree(third_party_include_dir, copy_autocxxpy_includes)
        copy_tree(autocxxpy_include_dir, copy_autocxxpy_includes)
        gtest_dir = os.path.join(copy_autocxxpy_includes, "gtest")
        gtest_dir = os.path.abspath(gtest_dir)
        shutil.rmtree(gtest_dir)


if __name__ == "__main__":
    main()
