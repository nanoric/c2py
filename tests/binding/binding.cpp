// binding.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include "pch.h"
#include <iostream>

#include <autocxxpy/autocxxpy.hpp>

using namespace std;
using namespace autocxxpy;

void callback(int, void *)
{
}

using callback_t = decltype(&callback);

void func(int, callback_t, void *)
{

}

PYBIND11_MODULE(binding, m)
{
    m.def("func", 
        autocxxpy::calling_wrapper_v<&func>
    );
}
