#pragma once

#include <memory>

#include <oes_api/oes_api.h>
#include <mds_api/mds_api.h>

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
};

#undef castto
