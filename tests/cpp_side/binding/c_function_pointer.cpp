// binding.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include "pch.h"
#include <iostream>

#include <c2py/c2py.hpp>
#include <boost/callable_traits.hpp>

#include <pybind11/pybind11.h>

#include <c2py/wrappers/c_function_callback.hpp>
#include <c2py/wrappers/string_array.hpp>
#include <c2py/calling_wrapper.hpp>

#include "binding.h"

using namespace c2py;

using callback_t = int(*)(int, void *);
const char ** const a = 0;

int func_1(int v, callback_t callback, void * user)
{
    return callback(v, user);
}

int func_4(int v, int, int, int, callback_t callback, void * user, int, int)
{
    return callback(v, user);
}


void prepare_function_pointer(pybind11::module &m)
{
    m.def("func_1",
        apply_function_transform<
        function_constant<&func_1>,
        brigand::list<indexed_transform_holder<c_function_callback_transform, 1>>
        >::value
    );
    m.def("func_4",
        apply_function_transform<
        function_constant<&func_4>,
        brigand::list<indexed_transform_holder<c_function_callback_transform, 4>>
        >::value
    );
}