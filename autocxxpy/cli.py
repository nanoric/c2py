import os
import re
import shutil
from distutils.dir_util import copy_tree
from typing import Callable, List

import click

import autocxxpy
from autocxxpy.core import CxxFileParser
from autocxxpy.core.core_types.generator_types import GeneratorFunction, GeneratorMethod, \
    GeneratorSymbol, GeneratorTypedef
from autocxxpy.core.preprocessor import PreProcessor, PreProcessorOptions
from autocxxpy.generator.cxxgenerator.cxxgenerator import CxxGenerator, CxxGeneratorOptions
from autocxxpy.generator.pyigenerator.pyigenerator import PyiGenerator
from autocxxpy.generator.setupgenerator.setupgenerator import SetupGenerator, SetupGeneratorOptions
from autocxxpy.objects_manager import ObjectManager
from autocxxpy.type_manager import TypeManager

my_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(my_dir, ".."))
autocxxpy_include_dir = os.path.join(my_dir, "include")
autocxxpy_include_dir = os.path.abspath(autocxxpy_include_dir)
third_party_include_dir = os.path.join(root_dir, "3rd_party", "include")
third_party_include_dir = os.path.abspath(third_party_include_dir)


@click.group()
def cli():
    pass


@cli.command(help="""
Converts C/C++ .h files into python module source files.
All matching is based on c++ qualified name, using regex.
""",
             )
# about input files
@click.argument("module-name",
                nargs=1
                )
@click.argument("files",
                type=click.Path(),
                nargs=-1
                )
@click.option("-e", "--encoding",
              help="encoding of input files, default is utf-8",
              default='utf-8'
              )
@click.option("-I", "--include-path", "include_dirs",
              help="additional include paths",
              multiple=True
              )
@click.option("-A", "--additional-include", "additional_includes",
              help="additional include files. These files will be included in output cxx file,"
                   " but skipped by parser.",
              multiple=True
              )
# about API detail
@click.option("-ew", "--string-encoding-windows",
              help="encoding used to get & set string."
                   " This value is used to construct std::locale."
                   " use `locale -a` to show all the locates supported."
                   " default is utf-8, which is the internal encoding used by pybind11.",
              default="utf-8",
              )
@click.option("-el", "--string-encoding-linux",
              help="encoding used to get & set string."
                   " This value is used to construct std::locale."
                   " use `locale -a` to show all the locates supported."
                   " default is utf-8, which is the internal encoding used by pybind11.",
              default="utf-8",
              )
# about modifier patterns
@click.option("-i", "--ignore-pattern",
              help="ignore symbols matched",
              )
@click.option("--no-callback-pattern",
              help="disable generation of callback for functions matched"
                   " (for some virtual method used as undocumented API)",
              )
@click.option("--no-transform-pattern",
              help="disable applying transforms(changing its signature) into functions matched"
                   " (for some virtual method used as callback only)",
              )
@click.option("--inout-arg-pattern",
              help="make symbol(arguments only) as input_output",
              )
@click.option("--output-arg-pattern",
              help="make symbol(arguments only) as output only",
              )
# about hacks
@click.option("--m2c/--no-m2c",
              help="treat const macros as global variable",
              default=True
              )
@click.option("--ignore-underline-prefixed/--no-ignore-underline-prefixed",
              help="ignore global variables starts with underline",
              default=True,
              )
@click.option("--ignore-unsupported/--no-ignore-unsupported",
              help="ignore functions that has unsupported argument",
              default=True,
              )
# about output style
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
@click.option("--clear-output-dir/--no-clear-output-dir",
              default=True,
              )
@click.option("--clear-pyi-output-dir/--no-clear-pyi-output-dir",
              default=True,
              )
@click.option("--copy-autocxxpy-includes",
              help="copy all autocxxpy include files, excluding input files to specific dir.",
              default="",
              )
@click.option("-m", "--max-lines-per-file",
              type=click.IntRange(min=200, clamp=True),
              default=500,
              )
# about setuo.py file
@click.option("--generate-setup",
              help="if set, generate setup.py into this location",
              default="",
              )
@click.option("--setup-lib-dir", "setup_lib_dirs",
              multiple=True,
              )
@click.option("--setup-lib", "setup_libs",
              multiple=True,
              )
@click.option("--setup-use-patches/--setup-no-use-patches",
              default=False,
              )
@click.option("--enforce-version",
              help="Check if autocxxpy version matches. If not match, print error and exit. "
                   "Use this to prevent generating code from incompatible version of autocxxpy.",
              default="",
              )
def generate(
    module_name: str,
    # input files
    files: List[str],
    encoding: str = 'utf-8',
    include_dirs: List[str] = None,
    additional_includes: List[str] = None,
    # api detail
    string_encoding_windows: str = "utf-8",
    string_encoding_linux: str = "utf-8",
    # patterns
    ignore_pattern: str = '',
    inout_arg_pattern: str = '',
    output_arg_pattern: str = '',
    no_callback_pattern: str = '',
    no_transform_pattern: str = '',
    # hacks
    m2c: bool = True,
    ignore_underline_prefixed: bool = True,
    ignore_unsupported: bool = True,
    # output style
    output_dir: str = 'generated_files',
    pyi_output_dir: str = '{output_dir}/{module_name}',
    clear_output_dir: bool = True,
    clear_pyi_output_dir: bool = False,
    copy_autocxxpy_includes: str = "",
    max_lines_per_file: bool = 500,
    # setup.py
    generate_setup: str = '',
    setup_lib_dirs: List[str] = None,
    setup_libs: List[str] = None,
    setup_use_patches: bool = False,
    enforce_version: str = '',
):
    if include_dirs is None:
        include_dirs = []
    if additional_includes is None:
        additional_includes = []
    if setup_lib_dirs is None:
        setup_lib_dirs = []
    if setup_libs is None:
        setup_libs = []

    print_version()

    if enforce_version:
        current_version = autocxxpy.__version__
        if enforce_version != current_version:
            print(f"version not match, required {enforce_version}, currently: {current_version}!")
            return

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

    type_manager = TypeManager(pre_processor_result.g, pre_processor_result.objects)

    def apply_filter(objects: ObjectManager, pattern: str,
                     callback: Callable[["ObjectManager", "GeneratorSymbol"], None]):
        if pattern:
            r = re.compile(pattern)
            for f in objects.values():  # type: GeneratorSymbol
                m = r.match(f.full_name)
                if m:
                    callback(objects, f)

    ignore_symbols: List[GeneratorSymbol] = []

    def ignore_name(objects: ObjectManager, s: "GeneratorSymbol"):
        ignore_symbols.append(s)
        s.generate = False

    def disable_callback(objects: ObjectManager, s: "GeneratorSymbol"):
        if isinstance(s, GeneratorMethod):
            s.is_final = True

    def disable_transform(objects: ObjectManager, s: "GeneratorSymbol"):
        if isinstance(s, GeneratorFunction):
            s.wrappers.clear()

    apply_filter(pre_processor_result.objects, ignore_pattern, ignore_name)

    apply_filter(pre_processor_result.objects, no_callback_pattern, disable_callback)
    apply_filter(pre_processor_result.objects, no_transform_pattern, disable_transform)

    if ignore_pattern:
        print(f"# of ignore: {len(ignore_symbols)}")
        for s in ignore_symbols:
            print(s.full_name)

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
    cxx_result.output(output_dir=output_dir, clear=clear_output_dir)

    pyi_result.output(output_dir=pyi_output_dir, clear=clear_pyi_output_dir)
    pyi_result.print_filenames()

    if copy_autocxxpy_includes:
        copy_tree(third_party_include_dir, copy_autocxxpy_includes)
        copy_tree(autocxxpy_include_dir, copy_autocxxpy_includes)
        gtest_dir = os.path.join(copy_autocxxpy_includes, "gtest")
        gtest_dir = os.path.abspath(gtest_dir)
        shutil.rmtree(gtest_dir)

    if generate_setup:
        setup_options = SetupGeneratorOptions(
            output_dir=output_dir,
            include_dirs=include_dirs,
            module_name=module_name,
            cxx_result=cxx_result,
            lib_dirs=setup_lib_dirs,
            libs=setup_libs,
            use_patches=setup_use_patches,
        )
        setup_result = SetupGenerator(setup_options).generate()
        setup_result.output(generate_setup)


@cli.command()
def version():
    print_version()


def print_version():
    print(f"autocxxpy {autocxxpy.__version__}")


if __name__ == '__main__':
    cli()
