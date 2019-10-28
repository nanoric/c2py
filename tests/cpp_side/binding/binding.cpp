
#include "pch.h"
#include <iostream>

#include <c2py/c2py.hpp>

#include <pybind11/pybind11.h>

#include "binding.h"

using namespace c2py;
using namespace pybind11;

PYBIND11_MODULE(binding, m)
{
    prepare_cross_assign(m); 
    prepare_function_pointer(m);
    prepare_array(m);
}
