// binding.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include "pch.h"
#include <iostream>

#include <c2py/c2py.hpp>
#include <boost/callable_traits.hpp>

#include <pybind11/pybind11.h>

#include <c2py/wrappers/string_array.h>

using namespace c2py;

template <auto m>
using method_constant = std::integral_constant<decltype(m), m>;

void func(char *arr[], int)
{
}

void func2(char *arr[], int, int, void *)
{
}


using func_t = decltype(&func);

static int __v = []()
{
    auto v1 = c2py::wrap_string_array<method_constant<&func>>();
    const char *s = "13";
    return 1;
}();

static void pybind11_test(pybind11::module &m)
{
    m.def("func", c2py::wrap_string_array<method_constant<&func>>());
    m.def("func", c2py::calling_wrapper_v<&func>);
}
