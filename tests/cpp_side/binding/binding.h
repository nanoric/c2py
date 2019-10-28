#include <iostream>

#include <c2py/c2py.hpp>

#include <pybind11/pybind11.h>


void prepare_function_pointer(pybind11::module& m);
void prepare_cross_assign(pybind11::module& m);
void prepare_array(pybind11::module& m);

