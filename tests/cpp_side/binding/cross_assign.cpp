
#include "pch.h"
#include <iostream>

#include <c2py/c2py.hpp>

#include <pybind11/pybind11.h>


using namespace c2py;
using namespace pybind11;

PYBIND11_MODULE(binding, m)
{
    cross_assign cs;
    object_store os;


    cs.record_assign(m, "attr", "::attr", "::a");
    cs.record_assign(m, "attr2", "::attr2", "::attr");

    os.emplace("::a", pybind11::int_(1234));

    cs.process_assign(os);
    // assert binding.attr == 1234
}
