#include <iostream>

#include <autocxxpy/autocxxpy.hpp>
#include <autocxxpy/base/type.h>
#include <autocxxpy/wrappers/string_array.hpp>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

using namespace autocxxpy;

static auto f(char **strs, int count)
{
    std::vector<std::string> s;
    for (int i = 0; i < count ; i++)
    {
        s.push_back(strs[i]);
    }
    return std::move(s);
}

static auto prefix_all(char *prefix, char **strs, int count)
{
    std::vector<std::string> ss;
    for (int i = 0; i < count ; i++)
    {
        std::string s = prefix;
        s += strs[i];
        ss.push_back(s);
    }
    return std::move(ss);
}

static auto append_all(char **strs, int count, char *suffix)
{
    std::vector<std::string> ss;
    for (int i = 0; i < count ; i++)
    {
        std::string s = strs[i];
        s += suffix;
        ss.push_back(s);
    }
    return std::move(ss);
}



template <class a,class b>
using transfrom = string_array_transform<a, b>;
PYBIND11_MODULE(wrap_string_array, m)
{
    using Method = function_constant<&f>;
    using Method2 = function_constant<&prefix_all>;
    using Method3 = function_constant<&append_all>;
    m.def("f", transfrom<Method, std::integral_constant<int, 0>>::value);
    m.def("prefix_all",
        apply_function_transform<
        Method2,
        brigand::list<
        indexed_transform_holder<transfrom, 1>
        >
        >::value
    );

    m.def("append_all",
        apply_function_transform <
        Method3,
        brigand::list<
        indexed_transform_holder<transfrom, 0>
        >
        >::value
    );
}