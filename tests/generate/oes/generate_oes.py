import logging

from autocxxpy.core.generator import GeneratorOptions, Generator
from autocxxpy.parser.cxxparser import CXXFileParser, CXXParseResult
from autocxxpy.core.preprocessor import GeneratorVariable, PreProcessor, PreProcessorOptions, \
    PreProcessorResult

logger = logging.getLogger(__file__)


def main():
    files = [
        'oes_api/oes_api.h',
        'mds_api/mds_api.h',
        'mds_api/core/json_parser/mds_json_parser.h',
    ]
    include_paths = ["vnoes/include"]
    parser_result: CXXParseResult = CXXFileParser(
        files=files,
        include_paths=include_paths,
    ).parse()

    # ignore some classes which is not used in python and not exist in linux
    parser_result.classes.pop('_spk_struct_timespec')
    parser_result.classes.pop('_spk_struct_timezone')
    parser_result.classes.pop('_spk_struct_iovec')
    parser_result.classes.pop('_spk_struct_timeval32')
    parser_result.classes.pop('_spk_struct_timeval64')

    # ignore some function we don't use
    parser_result.functions.pop('OesApi_WaitOnChannelGroup')
    parser_result.functions.pop('OesApi_SendBatchOrdersReq')
    parser_result.functions.pop('MdsApi_SubscribeByStringAndPrefixes')
    parser_result.functions.pop('MdsApi_SubscribeByStringAndPrefixes2')
    parser_result.functions.pop('MdsApi_SubscribeByString')
    parser_result.functions.pop('MdsApi_SubscribeByString2')
    parser_result.functions.pop('MdsApi_WaitOnTcpChannelGroup')
    parser_result.functions.pop('MdsApi_WaitOnTcpChannelGroupCompressible')
    parser_result.functions.pop('MdsApi_WaitOnUdpChannelGroup')

    # fix a union type inside MdsMktDataSnapshotT
    parser_result.classes['_MdsMktDataSnapshot'].variables.update(
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
    for c in parser_result.classes.values():
        for v in c.variables.values():
            if v.name == 'userInfo':
                v.type = 'int'

    # invoke pre_processor
    pre_process_options = PreProcessorOptions(parser_result)
    pre_process_options.treat_const_macros_as_variable = True
    pre_process_options.ignore_global_variables_starts_with_underline = True
    pre_processor = PreProcessor(pre_process_options)
    pre_process_result: PreProcessorResult = pre_processor.process()

    # options
    options = GeneratorOptions.from_preprocessor_result(
        "vnoes",
        pre_process_result,
        include_files=[*files, "custom/wrapper.hpp"]
    )
    options.max_lines_per_file = 20000

    # generate and output
    result = Generator(options=options).generate()
    result.output("vnoes/generated_files")

    return


if __name__ == "__main__":
    main()
