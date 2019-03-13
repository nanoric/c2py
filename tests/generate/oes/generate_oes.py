import logging
import os

from autocxxpy.cxxparser import CXXFileParser, CXXParseResult
from autocxxpy.generator import Generator, GeneratorOptions
from autocxxpy.preprocessor import GeneratorVariable, PreProcessor, PreProcessorOptions, \
    PreProcessorResult

logger = logging.getLogger(__file__)

oes_root = "vnoes/include"


def main():
    includes = [
        'oes_api/oes_api.h',
        'mds_api/mds_api.h',
        'mds_api/parser/json_parser/mds_json_parser.h',
    ]

    r0: CXXParseResult = CXXFileParser(
        includes,
        include_paths=[oes_root],
    ).parse()

    # ignore some classes not used and not exist in linux
    r0.classes.pop('_spk_struct_timespec')
    r0.classes.pop('_spk_struct_timezone')
    r0.classes.pop('_spk_struct_iovec')
    r0.classes.pop('_spk_struct_timeval32')
    r0.classes.pop('_spk_struct_timeval64')

    # ignore some ugly function
    r0.functions.pop('OesApi_SendBatchOrdersReq')
    r0.functions.pop('MdsApi_SubscribeByString2')
    r0.functions.pop('MdsApi_SubscribeByStringAndPrefixes2')

    r1: PreProcessorResult = PreProcessor(PreProcessorOptions(r0)).process()

    # options
    options = GeneratorOptions.from_preprocessor_result("vnoes", r1)
    options.includes.extend(includes)
    options.includes.append("custom/wrapper.hpp")
    options.split_in_files = True
    options.max_classes_in_one_file = 80

    # fix for hint unrecognized std::unique_ptr
    for c in options.classes.values():
        for v in c.variables.values():
            if v.name == 'userInfo':
                v.type = 'int'

    # fix a union type inside MdsMktDataSnapshotT
    options.classes['MdsMktDataSnapshotT'].variables.update({i.name: i for i in [
        GeneratorVariable(name='l2Stock', type='MdsL2StockSnapshotBodyT'),
        GeneratorVariable(name='l2StockIncremental', type='MdsL2StockSnapshotIncrementalT'),
        GeneratorVariable(name='l2BestOrders', type='MdsL2BestOrdersSnapshotBodyT'),
        GeneratorVariable(name='l2BestOrdersIncremental',
                          type='MdsL2BestOrdersSnapshotIncrementalT'),
        GeneratorVariable(name='stock', type='MdsStockSnapshotBodyT'),
        GeneratorVariable(name='option', type='MdsStockSnapshotBodyT'),
        GeneratorVariable(name='index', type='MdsIndexSnapshotBodyT'),
        GeneratorVariable(name='l2VirtualAuctionPrice', type='MdsL2VirtualAuctionPriceT'),
        GeneratorVariable(name='l2MarketOverview', type='MdsL2MarketOverviewT'),
    ]})

    Generator(options=options).generate().output("vnoes/generated_files")


if __name__ == "__main__":
    main()
