#!/usr/bin/env bash

python -m c2py vnxtp xtp_trader_api.h xtp_quote_api.h -I vnxtp/include  -o vnxtp/generated_files --no-callback-name .*Api
