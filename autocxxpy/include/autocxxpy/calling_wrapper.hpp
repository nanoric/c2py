#pragma once

#include "utils/functional.hpp"
#include "dispatcher.hpp"
#include <brigand/brigand.hpp>

#include "wrappers/cfunction.h"

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

    template <class T>
    struct default_transform : T {};

    template <template <class> class T>
    struct transform_holder
    {
        template <class Constant>
        using type = T<Constant>;
    };

    using trans_list = brigand::list <
        transform_holder<default_transform>
        , transform_holder< c_function_pointer_to_std_function>
    >;


    template <class T, class TransformHolder>
    struct apply_transform_element
    {
        template <class T>
        using transform = typename TransformHolder:: template type<T>;
        using type = typename transform<T>::type;
    };

    template <auto method>
    constexpr auto apply_transform_impl()
    {
        using namespace brigand;

        using result = fold<trans_list,
            std::integral_constant<decltype(method), method>,
            apply_transform_element<_state, _element>
        >;
        return result::value;
    }

    template <auto method>
    struct default_calling_wrapper
    {
    public:
        using ty = decltype(apply_transform_impl<method>());
        static constexpr ty value = apply_transform_impl<method>();
    };

    template <auto method>
    struct calling_wrapper : default_calling_wrapper<method>
    {};

    template <auto method>
    auto calling_wrapper_v = calling_wrapper<method>::value;
}
