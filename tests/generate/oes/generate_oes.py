import logging
import os

from autocxxpy.cxxparser import CXXFileParser, CXXParseResult
from autocxxpy.generator import Generator, GeneratorOptions
from autocxxpy.preprocessor import GeneratorVariable, PreProcessor, PreProcessorOptions, \
    PreProcessorResult

logger = logging.getLogger(__file__)

oes_root = "vnoes/include"


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
        ],
        include_paths=[oes_root],
    ).parse()

    # ignore some classes not used and not exist in linux
    r0.classes.pop('_spk_struct_timespec')
    r0.classes.pop('_spk_struct_timezone')
    r0.classes.pop('_spk_struct_iovec')
    r0.classes.pop('_spk_struct_timeval32')
    r0.classes.pop('_spk_struct_timeval64')

    r1: PreProcessorResult = PreProcessor(PreProcessorOptions(r0)).process()

    constants = {
        name: GeneratorVariable(**ov.__dict__)
        for name, ov in r0.variables.items()
    }
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
        for v in c.variables.values():
            if v.name == 'userInfo':
                v.type = 'int'
    classes['MdsMktDataSnapshotT'].variables.update({i.name: i for i in [
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

    options = GeneratorOptions(
        typedefs=r0.typedefs,
        constants=constants,
        functions=functions,
        classes=classes,
        dict_classes=r1.dict_classes,
        enums=enums,
        caster_class=r1.caster_class,
        split_in_files=True,
        max_classes_in_one_file=80,
    )
    options.includes.extend(includes)
    options.includes.append("custom/wrapper.hpp")

    options.module_name = "vnoes"

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
