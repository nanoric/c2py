import logging

from autocxxpy.generator.cxxgenerator.cxxgenerator import CxxGeneratorOptions, CxxGenerator
from autocxxpy.core.cxxparser import CXXFileParser
from autocxxpy.core.preprocessor import GeneratorVariable, PreProcessor, PreProcessorOptions, \
    PreProcessorResult

logger = logging.getLogger(__file__)


def main():
    files = [
        'oes_api/oes_api.h',
        'mds_api/mds_api.h',
        'mds_api/parser/json_parser/mds_json_parser.h',
    ]
    include_paths = ["vnoes/include"]
    parser = CXXFileParser(
        files=files,
        include_paths=include_paths,
    )
    print("parsing")
    parser_result = parser.parse()
    print("parse finished")

    # ignore some classes which is not used in python and not exist in linux
    parser_result.g.classes.pop('_spk_struct_timespec')
    parser_result.g.classes.pop('_spk_struct_timezone')
    parser_result.g.classes.pop('_spk_struct_iovec')
    parser_result.g.classes.pop('_spk_struct_timeval32')
    parser_result.g.classes.pop('_spk_struct_timeval64')

    # ignore some function we don't use
    parser_result.g.functions.pop('OesApi_WaitOnChannelGroup')
    parser_result.g.functions.pop('OesApi_SendBatchOrdersReq')
    parser_result.g.functions.pop('MdsApi_SubscribeByStringAndPrefixes')
    parser_result.g.functions.pop('MdsApi_SubscribeByStringAndPrefixes2')
    parser_result.g.functions.pop('MdsApi_SubscribeByString')
    parser_result.g.functions.pop('MdsApi_SubscribeByString2')
    parser_result.g.functions.pop('MdsApi_WaitOnTcpChannelGroup')
    parser_result.g.functions.pop('MdsApi_WaitOnTcpChannelGroupCompressible')
    parser_result.g.functions.pop('MdsApi_WaitOnUdpChannelGroup')

    # fix a union type inside MdsMktDataSnapshotT
    parser_result.g.classes['_MdsMktDataSnapshot'].variables.update(
        {i.name: i for i in [
            GeneratorVariable(name='l2Stock',
                              type='MdsL2StockSnapshotBodyT'),
            GeneratorVariable(name='l2StockIncremental',
                              type='MdsL2StockSnapshotIncrementalT'),
            GeneratorVariable(name='l2BestOrders',
                              type='MdsL2BestOrdersSnapshotBodyT'),
            GeneratorVariable(name='l2BestOrdersIncremental',
                              type='MdsL2BestOrdersSnapshotIncrementalT'),
            GeneratorVariable(name='stock',
                              type='MdsStockSnapshotBodyT'),
            GeneratorVariable(name='option',
                              type='MdsStockSnapshotBodyT'),
            GeneratorVariable(name='index',
                              type='MdsIndexSnapshotBodyT'),
            GeneratorVariable(name='l2VirtualAuctionPrice',
                              type='MdsL2VirtualAuctionPriceT'),
            GeneratorVariable(name='l2MarketOverview',
                              type='MdsL2MarketOverviewT'),
        ]})

    # fix for hint: unrecognized std::unique_ptr
    for c in parser_result.g.classes.values():
        for v in c.variables.values():
            if v.name == 'userInfo':
                v.type = 'int'

    # invoke pre_processor
    print("processing result")
    pre_process_options = PreProcessorOptions(parser_result)
    pre_process_options.treat_const_macros_as_variable = True
    pre_process_options.ignore_global_variables_starts_with_underline = True
    pre_processor = PreProcessor(pre_process_options)
    pre_process_result: PreProcessorResult = pre_processor.process()
    print("process finished")

    # options
    options = CxxGeneratorOptions.from_preprocessor_result(
        "vnoes",
        pre_process_result,
        include_files=[*files, "custom/wrapper.hpp"]
    )
    options.max_lines_per_file = 4000

    # generate and output
    print("generating code")
    result = CxxGenerator(options=options).generate()
    print("code generated")

    print("outputting result")
    result.output("vnoes/generated_files")
    result.print_filenames()

    return


if __name__ == "__main__":
    main()
