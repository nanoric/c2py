#!/usr/bin/env bash

my_dir=$(dirname "$0")
tests_dir=$my_dir/..
autocxxpy_dir=$tests_dir/..

PYTHONPATH=$autocxxpy_dir
export PYTHONPATH

python $tests_dir/python_side/parser/constant_type.py
python $tests_dir/python_side/parser/cross_scope_typedef.py
python $tests_dir/python_side/parser/extern_c.py
python $tests_dir/python_side/parser/namespace.py
python $tests_dir/python_side/parser/stl.py
python $tests_dir/python_side/parser/value_of_variable.py
