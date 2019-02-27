#pragma once

#include <memory>

#include <oes_api/oes_api.h>
#include <oes_api/parser/json_parser/oes_json_parser.h>
#include <mds_api/mds_api.h>
#include <mds_api/parser/json_parser/mds_json_parser.h>

struct helper
{
    static std::string mdstojson(
        SMsgHeadT *pRspHead,
        const void *pRspBody,
        const char *pRemoteInfo 
    )
    {
        const int size = 4096;
        char buf[size];
        auto retv = MdsJsonParser_EncodeRsp(pRspHead, (MdsMktRspMsgBodyT *)pRspBody, buf, size, pRemoteInfo);
        return buf;
    }
    static std::string oestojson(
        SMsgHeadT *pRspHead,
        const void *pRspBody,
        const char *pRemoteInfo 
    )
    {
        const int size = 4096;
        char buf[size];
        auto retv = OesJsonParser_EncodeRsp(pRspHead, (OesRspMsgBodyT *)pRspBody, buf, size, pRemoteInfo);
        return buf;
    }
};

#undef castto
