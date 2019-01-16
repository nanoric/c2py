#pragma once

#include <tuple>
#include <type_traits>

#include "dispatcher.h"

/*
example to change the calling method:

// switch async/direct
template <>
struct callback_type_of<static_cast<int(A::*)()>(&A::func2)>
{
    const static callback_type value = callback_type::Direct;
};


// rewrite the whole function
template<>
struct callback_wrapper<static_cast<int(A::*)(int)>(&A::func2)>
{
    inline static void call(A *instance, float)
    {
        constexpr auto method = static_cast<int(A::*)(int)>(&A::func2);
        default_callback_wrapper<method>::call(instance, 1);
        (instance->*method)(1);
        std::cout << "wrapped!" << std::endl;
    }
};

*/

template <int start_index = 0, class ... tuple_arg_types, class method_type, size_t ... idx >
inline std::invoke_result_t<method_type, tuple_arg_types ...> apply_tuple_impl(const method_type &method, std::tuple<tuple_arg_types...>&tuple, std::index_sequence<idx...>)
{
    return method(std::get<(idx + start_index)> (tuple) ... );
}

template <int start_index = 0, class ... tuple_arg_types, class method_type>
inline std::invoke_result_t<method_type, tuple_arg_types ...> apply_tuple(const method_type &method, std::tuple<tuple_arg_types...> &tuple)
{
    return apply_tuple_impl<start_index>(method, tuple, std::make_index_sequence<sizeof ... (tuple_arg_types) - start_index>{});
}


template <auto method>
struct value_invoke_result {
    template <class class_type, class ret_type, class ... arg_types>
    inline static ret_type get_type(ret_type(class_type::* m)(arg_types ...))
    {
    }
    template <class ret_type, class ... arg_types>
    inline static ret_type get_type(ret_type(*m)(arg_types ...))
    {
    }
    using type = decltype(get_type(method));
};

template <auto method>
using value_invoke_result_t = typename value_invoke_result<method>::type;


template <auto method>
struct class_of_member_method {
    template <class class_type, class ret_type, class ... arg_types>
    inline static class_type get_type(ret_type(class_type::* m)(arg_types ...))
    {
    }
    using type = decltype(get_type(method));
};

template <auto method>
using value_invoke_result_t = typename value_invoke_result<method>::type;

template <auto method>
using class_of_member_method_t = typename class_of_member_method<method>::type;


enum class callback_type
{
    Direct = 0,
    Async = 1
};


template <auto method>
struct default_callback_type_of
{
    const static callback_type value = callback_type::Async;
};
template <auto method>
struct callback_type_of: default_callback_type_of<method> {};


template <auto method>
constexpr callback_type callback_type_of_v = callback_type_of<method>::value;
template <auto method>
struct callback_wrapper_base
{
    using method_type = decltype(method);
    using ret_type = value_invoke_result_t<method>;
    using class_type = class_of_member_method_t<method>;

    static constexpr method_type _method = method;
public:
    template <class ... arg_types>
    inline static ret_type call(class_type *instance, arg_types ... args)
    {
    }

    template <class ... arg_types>
    inline static void async(class_type *instance, arg_types ... args)
    {
    }

    template <class ... arg_types>
    inline static ret_type sync(class_type *instance, arg_types ... args)
    {
    }
};

template <auto method>
struct default_callback_wrapper : callback_wrapper_base<method>
{
    using ret_type = value_invoke_result_t<method>;
    using class_type = class_of_member_method_t<method>;
public:
    template <class ... arg_types>
    inline static ret_type call(class_type *instance, arg_types ... args)
    {
        if constexpr (callback_type_of_v<method> == callback_type::Direct)
            return sync(instance, args ...);
        async(instance, args ...);
        return ret_type(); // if ret_type() is not constructable, this will make compiler unhappy
    }

    template <class ... arg_types>
    inline static void async(class_type *instance, arg_types ... args)
    {
        auto arg_tuple = make_async_arg_tuple(instance, args ...);
        auto task = [](auto tuple)
        {
            apply_tuple(&default_callback_wrapper::sync<arg_types ...>, tuple);
        };
        dispatcher::instance().add(std::move(task));
    }

    template <class ... arg_types>
    inline static ret_type sync(class_type *instance, arg_types ... args)
    {
        pybind11::gil_scoped_acquire gil;
        pybind11::function overload = pybind11::get_overload(static_cast<const class_type *>(instance), name);
        if (overload) {
            auto o = overload(args ...);
            if (pybind11::detail::cast_is_temporary_value_reference<ret_type>::value) {
                static pybind11::detail::overload_caster_t<ret_type> caster;
                return pybind11::detail::cast_ref<ret_type>(std::move(o), caster);
            }
            else return pybind11::detail::cast_safe<ret_type>(std::move(o));
        }
        return instance->*method(args ...);
    }
private:
    template <class T>
    inline static T &deref(const T *val)
    {
        return const_cast<T&>(*val);
    }

    template <class T>
    inline static T &deref(const T &val)
    {
        return const_cast<T&>(val);
    }

    template<class ... arg_types>
    inline static auto make_async_arg_tuple(arg_types ... args)->decltype(std::make_tuple(deref(args) ...))
    {
        return std::make_tuple(deref(args) ...);
    }
};
template <auto method>
struct callback_wrapper : default_callback_wrapper<method> {};

