#include <pybind11/pybind11.h>

#include "capsule.h"

using func = void(*)(int);

void init(pybind11::module &m)
{
    init_capsule(m, "capsule");
    printf("init!\n");
    m.def("test", [](func f) {
        f(1);

    });
    printf("test init!\n");
}