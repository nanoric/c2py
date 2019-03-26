
#include "pch.h"
#include <iostream>

#include <autocxxpy/autocxxpy.hpp>

#include <pybind11/pybind11.h>


using namespace autocxxpy;
using namespace pybind11;

PYBIND11_MODULE(binding, m)
{
    cross_assign cs;
    object_store os;


    cs.record_assign(m, "attr", "::a");

    os.emplace("::a", pybind11::int_(1234));

    cs.process_assign(os);
    // assert binding.attr == 1234
}
