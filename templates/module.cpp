#include <iostream>
#include <string>
#include <string_view>
#include <pybind11/pybind11.h>

#include "dispatcher.h"
#include "property_helper.h"
#include "wrapper_helper.h"
#include "class_generators.h"

$includes

$classes_generator_definitions

PYBIND11_MODULE(vnctptd, m)
{
$module_body
}
