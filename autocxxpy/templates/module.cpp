#include <iostream>
#include <string>
#include <pybind11/pybind11.h>
#include <autocxxpy/autocxxpy.hpp>

#include "module.hpp"
#include "generated_functions.h"

$includes

void additional_init(pybind11::module &m)
{
    autocxxpy::additional_init<$module_tag>::init(m);
}

void init_dispatcher(pybind11::module &m)
{
    autocxxpy::dispatcher::instance().start();
}

PYBIND11_MODULE($module_name, m)
{
$module_body
    additional_init(m);
    init_dispatcher(m);
}
