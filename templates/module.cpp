#include <iostream>
#include <string>
#include <string_view>
#include <pybind11/pybind11.h>
#include <ctp/ThostFtdcTraderApi.h>

#include "helper.h"
#include "wrapper.h"

$includes

PYBIND11_MODULE(vnctptd, m)
{
$module_body
}
