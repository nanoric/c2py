// binding.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include "pch.h"
#include <iostream>

#include <c2py/c2py.hpp>
#include <boost/callable_traits.hpp>

#include <pybind11/pybind11.h>

#include <c2py/property_helper.hpp>

#include <tuple>
#include "binding.h"

using namespace c2py;

struct tag {};
class A
{
public:
    int normal;
    int arr[10];
    int double_arr[10][10];
    int multi_arr[10][10][10];
    int* pointer;
};

void prepare_array(pybind11::module& m)
{
    //auto g = c2py::getter_wrap<tag, std::integral_constant<decltype(&A::multi_arr), &A::multi_arr>>::value;
    //auto s = c2py::setter_wrap<tag, std::integral_constant<decltype(&A::multi_arr), &A::multi_arr>>::value;
    ////A a;
    ////g(a);
    //std::vector<std::vector<std::vector<int>>> v3 = { {{10, 9, 8}, {7}} };
    //std::vector<std::vector<int>> v2={{10,9}, {8}};
    //std::vector<int> v1 = {7,6,7};
    //s(a, v3);

    pybind11::class_<
        A
    > c(m, "A");
    c.def(pybind11::init<>());

    static_assert(std::is_same_v<
        int,
        assign_value_type_t<int>
    >);
    static_assert(std::is_same_v<
        std::vector<int>,
        assign_value_type_t<int[10]>
    >);
    static_assert(std::is_same_v<
        std::vector<std::vector<int>>,
        assign_value_type_t<int[10][10]>
    >);
    static_assert(std::is_same_v<
        std::vector<std::vector<std::vector<int>>>,
        assign_value_type_t<int[10][10][10]>
    >);

    c.AUTOCXXPY_DEF_PROPERTY(tag, A, "arr", arr);
    c.AUTOCXXPY_DEF_PROPERTY(tag, A, "double_arr", double_arr);
    c.AUTOCXXPY_DEF_PROPERTY(tag, A, "multi_arr", multi_arr);
    //c.def_property("double_arr",
    //    c2py::getter_wrap<tag, std::integral_constant<decltype(&A::double_arr), &A::double_arr>>::value,
    //    c2py::setter_wrap<tag, std::integral_constant<decltype(&A::double_arr), &A::double_arr>>::value);
    //c.def_property("multi_arr",
    //    nullptr,
    //    //c2py::getter_wrap<tag, std::integral_constant<decltype(&A::multi_arr), &A::multi_arr>>::value,
    //    c2py::setter_wrap<tag, std::integral_constant<decltype(&A::multi_arr), &A::multi_arr>>::value);
    //    //nullptr);
}

