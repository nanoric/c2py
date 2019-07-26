#!/usr/bin/env bash

my_dir=`dirname "$0"`
tests_dir=$my_dir/..
c2py_dir=$tests_dir/..

PYTHONPATH=$c2py_dir
export PYTHONPATH

pushd $tests_dir/python_side/parser
for f in `ls *.py`; do
    python $f
done

