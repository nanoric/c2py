#!/usr/bin/env bash

python -m c2py vnoes oes_api/oes_api.h mds_api/mds_api.h -I vnoes/include  -o vnoes/generated_files --no-callback-name .*
