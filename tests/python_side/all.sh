#!/usr/bin/env bash

my_dir=`dirname "$0"`
tests_dir=$my_dir/..
autocxxpy_dir=$tests_dir/..

PYTHONPATH=$autocxxpy_dir
export PYTHONPATH

pushd $tests_dir/python_side/parser
for f in `ls *.py`; do
    python $f
done

