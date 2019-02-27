#include <iostream>
#include <string>
#include <pybind11/pybind11.h>
#include <autocxxpy/autocxxpy.hpp>

#include "module.hpp"
#include "class_generators.h"

$includes

void init_dispatcher(pybind11::module &m)
{
    autocxxpy::dispatcher::instance().start();
}

void generate_classes(pybind11::module &m)
{
$classes_code
}

void generate_functions(pybind11::module &m)
{
$functions_code
}

void generate_enums(pybind11::module &m)
{
$enums_code
}

void generate_constants(pybind11::module &m)
{
$constants_code
}

void init_caster(pybind11::module &m)
{
$casters_code
}

// begin generated code - combined_class_generator_definitions
// code will appear only when split_in_files is off
$combined_class_generator_definitions
// end generated code


void additional_init(pybind11::module &m)
{
    autocxxpy::additional_init<$module_tag>::init(m);
}

PYBIND11_MODULE($module_name, m)
{
    generate_classes(m);
    generate_functions(m);
    generate_constants(m);
    generate_enums(m);
    init_caster(m);

    additional_init(m);

    init_dispatcher(m);
}
