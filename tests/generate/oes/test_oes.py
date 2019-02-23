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

OesApi_SetCustomizedDriverId("C02TL13QGVC8")

env = OesApiClientEnvT()


# res = OesApi_InitAll(env, 'oes_client_sample.ini',
#                      OESAPI_CFG_DEFAULT_SECTION_LOGGER,
#                      OESAPI_CFG_DEFAULT_SECTION,
#                      OESAPI_CFG_DEFAULT_KEY_ORD_ADDR,
#                      OESAPI_CFG_DEFAULT_KEY_RPT_ADDR,
#                      OESAPI_CFG_DEFAULT_KEY_QRY_ADDR,
#                      0, 0
#                      )


def callback(pSessionInfo: SGeneralClientChannelT,
             pMsgHead: SMsgHeadT,
             pMsgBody: Any):
    return 1


res = OesApi_WaitReportMsg(env.qryChannel, 100, callback)

pass
