#pragma once

#include <tuple>
#include <type_traits>

#include "dispatcher.hpp"

namespace autocxxpy
{

    /*
    example to change the calling method:

    @startcode pp
    template <>
    struct calling_wrapper<&A::func2>
    {
        static constexpr auto value = [](){return 1;};
    };
    @endcode
    */
    template <auto method>
    struct default_calling_wrapper
    {
    public:
        using ret_type = value_invoke_result_t<method>;
        using func_type = decltype(method);
    public:
        static constexpr func_type value = method;
    };

    template <auto method>
    struct calling_wrapper : default_calling_wrapper<method>
    {};
}
