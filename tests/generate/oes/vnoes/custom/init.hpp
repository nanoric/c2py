#pragma once


#include <autocxxpy/autocxxpy.hpp>
#include <pybind11/pybind11.h>

#include <oes_api/oes_api.h>

#include "../init.h"
#include "../generated_files/class_generators.h"
#include "generated_files/module.hpp"

namespace autocxxpy
{
    template <>
    struct additional_init<tag_vnoes>
    {
        static void init(pybind11::module &m)
        {
            ::init(m);
        }
    };
}
