#pragma once

#include <memory>

#include <oes_api/oes_api.h>
#include <oes_api/parser/json_parser/oes_json_parser.h>
#include <mds_api/mds_api.h>
#include <mds_api/parser/json_parser/mds_json_parser.h>

#define castto(name) \
inline static std::unique_ptr<name> to##name(void *ptr)\
{\
    return std::make_unique<name>(*(name *)ptr);\
}\

struct helper
{
    castto(MdsMktRspMsgBodyT);
    castto(OesStkHoldingItemT);
    castto(OesCashAssetItemT);
    castto(OesStockItemT);
    castto(OesMarketStateItemT);
    castto(OesRspMsgBodyT);
    static char *toString(void *ptr)
    {
        return (char *)ptr;
    }
    static std::string tostr(void *ptr)
    {
        return (char *)ptr;
    }
    static void *allocate(int size)
    {
        auto p = new char[size];
        memset(p, 0, size);
        return p;
    }
    static void free(void *ptr)
    {
        delete ptr;
    }
    static const char * mdstojson(
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
    static const char * oestojson(
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
