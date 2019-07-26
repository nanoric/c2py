#include <iostream>

#include <c2py/c2py.hpp>
#include <c2py/base/type.h>
#include <c2py/wrappers/output_argument.hpp>

#include <pybind11/pybind11.h>

using namespace c2py;

static void f(int* a)
{
    *a = 1;
}

static int f2(int* a, int *b)
{
    *a = 11;
    *b = 12;
    return 1;
}

static int f3(int* a, int *b, int *c)
{
    *a = 21;
    *b = 22;
    *c = 23;
    return 1;
}

PYBIND11_MODULE(wrap_argument_as_output, m)
{
    using Method = function_constant<&f>;
    using Method2 = function_constant<&f2>;
    using Method3 = function_constant<&f3>;
    m.def("f", output_argument_transform<Method, std::integral_constant<int, 0>>::value);
    m.def("f2",
        apply_function_transform<
        function_constant<&f2>,
        brigand::list<
        indexed_transform_holder<output_argument_transform, 0>,
        indexed_transform_holder<output_argument_transform, 0>
        >
        >::value
    );

    m.def("f3",
        apply_function_transform<function_constant<&f3>,
        brigand::list<
        indexed_transform_holder<output_argument_transform, 0>,
        indexed_transform_holder<output_argument_transform, 0>,
        indexed_transform_holder<output_argument_transform, 0>
        >
        >::value
    );
}