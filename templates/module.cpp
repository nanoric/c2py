#include <iostream>
#include <string>
#include <string_view>
#include <pybind11/pybind11.h>
#include <ctp/ThostFtdcTraderApi.h>

$includes
#include "helper.h"
#include "wrapper.h"
#include "converts.h"

PYBIND11_MODULE(vnctptd, m)
{
$module_body
}
