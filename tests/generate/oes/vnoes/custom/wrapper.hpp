#pragma once

#include <autocxxpy/autocxxpy.hpp>

#include <oes_api/oes_api.h>
#include <mds_api/mds_api.h>

namespace autocxxpy
{
    //template <>
    //struct calling_wrapper<&::OesApi_WaitReportMsg>
    //{
    //    static constexpr auto value = [](
    //        OesApiSessionInfoT *pRptChannel,
    //        int32 timeoutMs,
    //        F_OESAPI_ON_RPT_MSG_T pRptMsgCallback,
    //        void *pCallbackParams
    //        )
    //    {
    //        return ::OesApi_WaitReportMsg(pRptChannel, timeoutMs, pRptMsgCallback, pCallbackParams);
    //    };
    //};

    template <>
    struct calling_wrapper<&::OesApi_WaitOnChannelGroup>
    {
        static constexpr auto value = [](
            OesApiChannelGroupT *pChannelGroup,
            int32 timeoutMs,
            F_OESAPI_ON_RPT_MSG_T pOnMsgCallback,
            void *pCallbackParams
            )
        {
            return ::OesApi_WaitOnChannelGroup(pChannelGroup, timeoutMs, pOnMsgCallback, pCallbackParams, nullptr);
        };
    };

    template <>
    struct calling_wrapper<&::MdsApi_WaitOnTcpChannelGroup>
    {
        static constexpr auto value = [](
            MdsApiChannelGroupT *pChannelGroup,
            int32 timeoutMs,
            F_MDSAPI_ONMSG_T pOnMsgCallback,
            void *pCallbackParams
            )
        {
            return ::MdsApi_WaitOnTcpChannelGroup(pChannelGroup, timeoutMs, pOnMsgCallback, pCallbackParams, nullptr);
        };
    };

    template <>
    struct calling_wrapper<&::MdsApi_WaitOnTcpChannelGroupCompressible>
    {
        static constexpr auto value = [](
            MdsApiChannelGroupT *pChannelGroup,
            int32 timeoutMs,
            F_MDSAPI_ONMSG_T pOnMsgCallback,
            void *pCallbackParams
            )
        {
            return ::MdsApi_WaitOnTcpChannelGroupCompressible(pChannelGroup, timeoutMs, pOnMsgCallback, pCallbackParams, nullptr);
        };
    };

    template <>
    struct calling_wrapper<&::MdsApi_WaitOnUdpChannelGroup>
    {
        static constexpr auto value = [](
            MdsApiChannelGroupT *pChannelGroup,
            int32 timeoutMs,
            F_MDSAPI_ONMSG_T pOnMsgCallback,
            void *pCallbackParams
            )
        {
            return ::MdsApi_WaitOnUdpChannelGroup(pChannelGroup, timeoutMs, pOnMsgCallback, pCallbackParams, nullptr);
        };
    };
}
