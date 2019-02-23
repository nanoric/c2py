import os

# noinspection PyUnresolvedReferences
from typing import *

mydir = os.path.split(__file__)[0]
dll_dir = os.path.join(mydir, "oes_libs-0.15.7.4-release", "win64")
path = os.getenv("PATH")
os.putenv('PATH', f"{dll_dir};{path}")

# noinspection PyUnresolvedReferences
import vnoes
from vnoes import *


def MdsApiSample_ResubscribeByCodePrefix(channel, pCodeListString):
    SSE_CODE_PREFIXES = \
        "009, 01, 02, " + \
        "10, 11, 12, 13, 18, 19, " + \
        "20, " + \
        "5, " + \
        "6, " + \
        "#000"
    SZSE_CODE_PREFIXES = \
        "00, " + \
        "10, 11, 12, 13, " + \
        "15, 16, 17, 18, " + \
        "30" + \
        "39"

    MdsApi_SubscribeByStringAndPrefixes(channel,
                                        pCodeListString,
                                        None,
                                        SSE_CODE_PREFIXES,
                                        SZSE_CODE_PREFIXES,
                                        eMdsSecurityTypeT.MDS_SECURITY_TYPE_STOCK,
                                        eMdsSubscribeModeT.MDS_SUB_MODE_SET,
                                        eMdsSubscribeDataTypeT.MDS_SUB_DATA_TYPE_L1_SNAPSHOT \
                                        | eMdsSubscribeDataTypeT.MDS_SUB_DATA_TYPE_L2_SNAPSHOT \
                                        |eMdsSubscribeDataTypeT.MDS_SUB_DATA_TYPE_L2_BEST_ORDERS\
                                        |eMdsSubscribeDataTypeT.MDS_SUB_DATA_TYPE_L2_ORDER\
                                        |eMdsSubscribeDataTypeT.MDS_SUB_DATA_TYPE_L2_TRADE
                                        )


env = MdsApiClientEnvT()
MdsApi_InitAllByConvention(env, "mds_client.ini")

a = 1 | 2 | 3
MdsApiSample_ResubscribeByCodePrefix(env.qryChannel, "600000, 600001, 000001, 0000002.SZ")


def MdsApiSample_HandleMsg(pSessionInfo: SGeneralClientChannelT,
                           pMsgHead: SMsgHeadT,
                           pMsgBody: Any):
    body = cast.toMdsMktRspMsgBodyT(pMsgBody)
    return 0


while True:
    ret = MdsApi_WaitOnMsg(env.tcpChannel, 1000, MdsApiSample_HandleMsg)
    if ret and not ret:
        break
MdsApi_LogoutAll(env, True)
MdsApi_DestoryAll(env)

vnoes.__SPlatform_GetErrno()

