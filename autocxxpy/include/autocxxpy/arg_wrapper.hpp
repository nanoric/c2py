#pragma once

#include "utils/functional.hpp"
#include "utils/type_sequence.hpp"
#include "arg_wrapper.hpp"
#include "dispatcher.hpp"

namespace autocxxpy
{

    /*
    example to change the argument wrapper:

    */

    template <class ty>
    struct default_binding_type {
        using type = ty;
    };


    template <class type>
    struct binding_type : default_binding_type<type> {};

    template <class type>
    using binding_type_t = typename binding_type<type>::type;


    template <class binding_type, class cpp_type>
    struct resolver
    {
        inline cpp_type&& operator()(binding_type &&v)
        {
            return std::forward<binding_type>(v);
        }
    };

    //-------------------------------

    template <class ret_type, class ... arg_types>
    struct function_pointer_wrapper
    {
        using func_t = ret_type(*)(arg_types...);
        function_pointer_wrapper(func_t func)
        {
        }
    };

    template <class cpp_ret_type, class ... cpp_arg_types>
    struct default_binding_type<cpp_ret_type(*)(cpp_arg_types ...)>
    {
        using type = function_pointer_wrapper<cpp_ret_type, cpp_arg_types ...>;
    };

    //template <class class_type, class cpp_ret_type, class ... cpp_arg_types>
    //struct default_binding_type<cpp_ret_type(class_type::*)(cpp_arg_types ...)> {
    //    using type = std::function<cpp_ret_type(class_type &, cpp_arg_types ...)>&;
    //};

    template <class cpp_ret_type, class ... cpp_arg_types>
    struct resolver<binding_type_t<cpp_ret_type(*)(cpp_arg_types ...)>, cpp_ret_type(*)(cpp_arg_types ...)>
    { // match function pointer
        using binding_type = binding_type_t<cpp_ret_type(*)(cpp_arg_types ...)>; // resolver
        using cpp_type = cpp_ret_type(*)(cpp_arg_types ...);
        inline cpp_type&& operator()(binding_type &&v)
        {
            return [](cpp_arg_types ... args)->cpp_ret_type
            {
                return cpp_ret_type{};
                // # todo: all these args should be resolve too.
                //return v(std::forward<cpp_arg_types>(args) ...);
            };
        }
    };
}
