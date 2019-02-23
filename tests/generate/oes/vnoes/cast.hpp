#pragma once

#include <oes_api/oes_api.h>
#include <mds_api/mds_api.h>

#define castto(name) \
inline static name *to##name(void *ptr)\
{\
    return (name *)(ptr);\
}\

struct cast
{
    castto(MdsMktRspMsgBodyT);
    castto(OesStkHoldingItemT);
    castto(OesCashAssetItemT);
    castto(OesStockItemT);
    castto(OesMarketStateItemT);
    castto(OesRspMsgBodyT);
};

#undef castto
