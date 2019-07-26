// binding.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include "pch.h"
#include <iostream>

#include <c2py/c2py.hpp>
#include <boost/callable_traits.hpp>

#include <pybind11/pybind11.h>

#include <c2py/wrappers/cfunction.h>
#include <c2py/wrappers/string_array.h>

using namespace c2py;

using callback_t = int(*)(int, void *);
const char ** const a = 0;

int func(int v, callback_t callback, void * user)
{
    return callback(v, user);
}

int func2(int v, int, int, int, callback_t callback, void * user, int, int)
{
    return callback(v, user);
}


int nofail1(void)
{
    return 1;
}

int nofail2(int v, callback_t callback, int)
{
    return 1;
}


int nofail3(int v, callback_t callback)
{
    return 1;
}

static void c_function_pointer(pybind11::module &m)
{
    m.def("func",
        c2py::calling_wrapper_v<&func>
        //c2py::c_function_pointer_to_std_function<std::integral_constant<decltype(&func), &func>>::value
        //c2py::wrap_c_function_ptr<&func>()
    );
    m.def("func2",
        c2py::calling_wrapper_v<&func2>
    );

    c2py::calling_wrapper_v<&nofail1>;
    c2py::calling_wrapper_v<&nofail2>;
    c2py::calling_wrapper_v<&nofail3>;
}