
#include "pch.h"
#include <iostream>

#include <c2py/c2py.hpp>

#include <pybind11/pybind11.h>

#include "binding.h"

using namespace c2py;
using namespace pybind11;

void prepare_cross_assign(pybind11::module& m)
{
    cross_assign cs;
    object_store os;


    cs.record_assign(m, "attr", "::attr", "::a");  // assert binding.attr == 1234
    cs.record_assign(m, "attr2", "::attr2", "::attr"); // assert bniding.attr2 == 1234

    os.emplace("::a", pybind11::int_(1234));

    cs.process_assign(os);
}
