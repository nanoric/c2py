#include <iostream>

#include <autocxxpy/autocxxpy.hpp>
#include <autocxxpy/base/type.h>
#include <autocxxpy/wrappers/string_array.hpp>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

using namespace autocxxpy;

using callback1_t = int(*)(void *);
static int f(callback1_t callback, void * user)
{
    return callback(user);
}

using callback2_t = int(*)(int, void *);
static int f2(int v, callback2_t callback, void * user)
{
    return callback(v, user);
}


using callback3_t = int(*)(int, int, int, void *);
static int f3(int v, callback3_t callback, void * user, int v2, int v3)
{
    return callback(v, v2, v3, user);
}



template <class a, class b>
using transfrom = c_function_callback_transform<a, b>;
PYBIND11_MODULE(wrap_c_function_callback, m)
{
    using Method = function_constant<&f>;
    using Method2 = function_constant<&f2>;
    using Method3 = function_constant<&f3>;
    m.def("f", transfrom<Method, std::integral_constant<int, 0>>::value);
    m.def("f2",
        apply_function_transform<
        Method2,
        brigand::list<
        indexed_transform_holder<transfrom, 1>
        >
        >::value
    );
    m.def("f3",
        apply_function_transform<
        Method3,
        brigand::list<
        indexed_transform_holder<transfrom, 1>
        >
        >::value
    );
}