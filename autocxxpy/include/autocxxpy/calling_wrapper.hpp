#pragma once

#include "utils/functional.hpp"
#include "utils/type_sequence.hpp"
#include "arg_wrapper.hpp"
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
    struct binding_type_sequence {
        template <class class_type, class ret_type, class ... arg_types>
        inline static auto get_type(ret_type(class_type::* m)(arg_types ...)) noexcept
        {
            return type_sequence<binding_type_t<arg_types>...>{};
        }
        template <class ret_type, class ... arg_types>
        inline static auto get_type(ret_type(*m)(arg_types ...)) noexcept
        {
            return type_sequence<binding_type_t<arg_types>...>{};
        }
        using type = decltype(get_type(method));
    };

    template <auto method>
    using binding_type_sequence_for = typename binding_type_sequence<method>::type;


    //template <auto method>
    //struct cpp_types {
    //    template <class class_type, class ret_type, class ... arg_types>
    //    inline static auto get_type(ret_type(class_type::* m)(arg_types ...)) noexcept
    //    {
    //        return type_sequence<cpp_type_t<arg_types>...>{};
    //    }
    //    template <class ret_type, class ... arg_types>
    //    inline static auto get_type(ret_type(*m)(arg_types ...)) noexcept
    //    {
    //        return type_sequence<cpp_type_t<arg_types>...>{};
    //    }
    //    using type = decltype(get_type(method));
    //};

    //template <auto method>
    //using cpp_types_t = typename cpp_types<method>::type;

    template <class cpp_ret_type, class ... cpp_arg_types>
    struct default_calling_wrapper_impl
    {
        constexpr default_calling_wrapper_impl(cpp_ret_type(*const m)(cpp_arg_types ...))
            :m(m)
        {
        }

        auto operator ()(binding_type_t<cpp_arg_types> &&... binding_args)
        {
            m(
                resolver<binding_type_t<cpp_arg_types>, cpp_arg_types>{}(
                    std::forward<binding_type_t<cpp_arg_types>>(binding_args)
                    ) ...
            );
        };
    private:
        cpp_ret_type(*const m)(cpp_arg_types ...);
    };

    template <auto method>
    struct default_calling_wrapper
    {
        using impl_type = decltype(default_calling_wrapper_impl(method));
        static constexpr impl_type value = default_calling_wrapper_impl(method);
    };

    template <auto method>
    struct calling_wrapper : default_calling_wrapper<method>
    {};

    template <auto method>
    auto calling_wrapper_v = calling_wrapper<method>::value;
}
