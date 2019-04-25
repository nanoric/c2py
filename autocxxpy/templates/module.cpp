#include <iostream>
#include <string>
#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <autocxxpy/autocxxpy.hpp>

#include "module.hpp"
#include "generated_functions.h"

$includes

autocxxpy::cross_assign $module_class::cross;
autocxxpy::object_store $module_class::objects;

void additional_init(pybind11::module &m)
{
    autocxxpy::additional_init<$module_tag>::init(m);
}

void init_dispatcher(pybind11::module &m)
{
    m.def("set_async_callback_exception_handler", &autocxxpy::async_callback_exception_handler::set_handler);
    autocxxpy::dispatcher::instance().start();
}

PYBIND11_MODULE($module_name, m)
{
$module_body
    $module_class::process_post_assign();

    additional_init(m);
    init_dispatcher(m);
}
