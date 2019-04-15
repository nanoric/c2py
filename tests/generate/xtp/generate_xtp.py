import logging

from autocxxpy.generator.cxxgenerator.cxxgenerator import CxxGeneratorOptions, CxxGenerator
from autocxxpy.core.cxxparser import CxxFileParser
from autocxxpy.core.preprocessor import GeneratorVariable, PreProcessor, PreProcessorOptions, \
    PreProcessorResult
from autocxxpy.generator.pyigenerator.pyigenerator import PyiGenerator

logger = logging.getLogger(__file__)


def main():
    files = [
        "xtp_quote_api.h",
        "xtp_trader_api.h", 
    ]
    include_paths = ["vnxtp/include"]
    parser = CxxFileParser(
        files=files,
        include_paths=include_paths,
    )
    print("parsing")
    parser_result = parser.parse()
    print("parse finished")

    # invoke pre_processor
    print("processing result")
    pre_process_options = PreProcessorOptions(parser_result)
    pre_process_options.treat_const_macros_as_variable = True
    pre_process_options.ignore_global_variables_starts_with_underline = True
    pre_processor = PreProcessor(pre_process_options)
    pre_process_result: PreProcessorResult = pre_processor.process()
    print("process finished")
    pre_process_result.print_unsupported_functions()

    # options
    options = CxxGeneratorOptions.from_preprocessor_result(
        "vnxtp",
        pre_process_result,
        include_files=[*files, ]
    )
    options.max_lines_per_file = 4000

    # generate and output
    print("generating code")
    result = CxxGenerator(options=options).generate()
    print("code generated")

    print("outputting result")
    result.output("vnxtp/generated_files")
    result.print_filenames()

    result = PyiGenerator(options=options).generate()
    result.output("vnxtp/generated_files")
    result.print_filenames()


    return


if __name__ == "__main__":
    main()
