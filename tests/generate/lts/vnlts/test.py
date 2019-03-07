import code
import os

# noinspection PyUnresolvedReferences
from typing import Any

import vnlts
# noinspection PyUnresolvedReferences
from vnlts import (CSecurityFtdcDepthMarketDataField, CSecurityFtdcMdApi,
                   CSecurityFtdcMdSpi, CSecurityFtdcReqUserLoginField,
                   CSecurityFtdcRspInfoField, CSecurityFtdcRspUserLoginField,
                   CSecurityFtdcSpecificInstrumentField, CSecurityFtdcUserLogoutField)

path = '.'
api = CSecurityFtdcMdApi.CreateFtdcMdApi(str(os.path.join(path, "td")))


class MdSpi(CSecurityFtdcMdSpi):

    def OnFrontConnected(self):
        print("connected")


spi = MdSpi()
api.RegisterSpi(spi)
api.RegisterFront("tcp://www.baidu.com:80")
api.Init()

code.interact(local=locals())
