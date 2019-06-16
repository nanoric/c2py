#!/usr/bin/env bash

autocxxpy vnctp                                                     \
    ThostFtdcMdApi.h                                                \
    ThostFtdcTraderApi.h                                            \
    ThostFtdcUserApiDataType.h                                      \
    ThostFtdcUserApiStruct.h                                        \
    -I                          vnctp/include/                      \
    -I                          vnctp/include/generated_includes/   \
    --no-callback-pattern       ".*Api::.*"                         \
    --string-encoding-windows   .936                                \
    --string-encoding-linux     zh_CN.GB18030                       \
                                                                    \
    --copy-autocxxpy-includes   vnctp/include/generated_includes/   \
    --output-dir                vnctp/generated_files/              \
    --clear-output-dir                                              \
                                                                    \
    --generate-setup            .                                   \
    --setup-lib-dir             vnctp/libs/                         \
    --setup-lib                 thostmduserapi                      \
    --setup-lib                 thosttraderapi                      \
    --setup-use-patches

