#pragma once

#include <type_traits>

namespace c2py
{
    template <class element, size_t size>
    using literal_array = element[size];

    template <class type>
    struct is_literal_array : std::false_type {};

    template <class element, size_t size>
    struct is_literal_array<literal_array<element,size>> : std::true_type {};

    template <class type>
    constexpr bool is_literal_array_v = is_literal_array<type>::value;
    

    // specialization for char[]
    template <size_t size>
    using string_literal = literal_array<char, size>;

    template <size_t size>
    using const_string_literal = literal_array<const char, size>;

    template <auto method>
    using function_constant = std::integral_constant<decltype(method), method>;
}