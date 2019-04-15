import re
from typing import List, TYPE_CHECKING

import click

from autocxxpy.core import CxxFileParser
from autocxxpy.core.preprocessor import PreProcessor, PreProcessorOptions
from autocxxpy.generator.cxxgenerator.cxxgenerator import CxxGenerator, CxxGeneratorOptions
from autocxxpy.generator.pyigenerator.pyigenerator import PyiGenerator

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from autocxxpy.core.types.generator_types import GeneratorSymbol  # noqa


@click.command()
@click.argument("module-name",
                nargs=1
                )
@click.argument("files",
                type=click.Path(),
                nargs=-1
                )
@click.option("-o", "--output-dir",
              help="output directory",
              type=click.Path(),
              nargs=1,
              default="generated_files",
              )
@click.option("-I", "--include-path", "includes",
              help="additional include paths",
              multiple=True)
@click.option("-i", "--ignore-name", "ignore_names",
              help="ignore symbols match this name(cxx qualified name), use regex pattern to match",
              multiple=True,
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
    "--max-lines-per-file",
    type=int,
    default=8000,
)
@click.option(
    "--clear-output/--no-clear-output",
    default=True,
)
def main(
    module_name: str,
    files: List[str],
    output_dir: str,
    includes: List[str],
    ignore_names: List[str],
    m2c: bool,
    ignore_underline_prefixed: bool,
    ignore_unsupported: bool,
    max_lines_per_file: bool,
    clear_output: bool = True,
):
    print("parsing ...")
    parser = CxxFileParser(files=files, include_paths=includes)
    parser_result = parser.parse()
    print("parse finished.")

    print()
    print("processing result ...")
    pre_processor_options = PreProcessorOptions(parser_result)
    pre_processor_options.treat_const_macros_as_variable = m2c
    pre_processor_options.ignore_global_variables_starts_with_underline = ignore_underline_prefixed
    pre_processor_options.ignore_unsupported_functions = ignore_unsupported
    pre_processor_result = PreProcessor(pre_processor_options).process()
    print("process finished.")
    pre_processor_result.print_unsupported_functions()

    if ignore_names:
        for name in ignore_names:
            r = re.compile(name)
            for f in pre_processor_result.objects.values():  # type: GeneratorSymbol
                m = r.match(f.full_name)
                if m:
                    f.generate = False

    print()
    print("generating cxx code ...")
    options = CxxGeneratorOptions.from_preprocessor_result(
        module_name=module_name,
        pre_processor_result=pre_processor_result,
        include_files=files,
    )
    options.max_lines_per_file = max_lines_per_file
    cxx_result = CxxGenerator(options=options).generate()
    print("cxx code generated.")

    print()
    print("generating pyi code ...")
    pyi_result = PyiGenerator(options=options).generate()
    print("pyi code generated.")

    cxx_result.print_filenames()
    cxx_result.output(output_dir=output_dir, clear=clear_output)

    pyi_result.output(output_dir=output_dir, clear=False)
    pyi_result.print_filenames()


if __name__ == "__main__":
    main()
