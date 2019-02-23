#pragma once

#include <tuple>

namespace autocxxpy
{
    template <class ... args>
    using type_sequence = std::tuple<args...>;

    //template <class ... types>
    //struct type_sequence : std::tuple<types ...>
    //{
    //    using type = type_sequence<types ...>;
    //};


    template<class ...args>
    struct type_seq_concat
    {
        using type = type_sequence<args ...>;
    };


    template<class ...args, class ... a2>
    struct type_seq_concat<type_sequence<args ...>, type_sequence<a2 ...>>
    {
        using type = type_sequence<args ..., a2...>;
    };

    template<class ...args, class ... a2>
    struct type_seq_concat<type_sequence<args ...>, a2 ...>
    {
        using type = type_sequence<args ..., a2...>;
    };

    template<class ...args>
    struct type_seq_concat<type_sequence<args ...>>
    {
        using type = type_sequence<args ...>;
    };

    template <class ... args>
    constexpr int types_size()
    {
        return std::tuple_size_v<std::tuple<args...>>;
    }

    // get index of ty in types ...
    // return -1 if not found
    template <class ty>
    constexpr int type_index()
    {
        return -1;
    }

    template <class ty, class arg, class ... args>
    constexpr int type_index(std::enable_if_t<std::is_same_v<ty, arg>, int> = 0)
    {
        return 0;
    }

    template <class ty, class arg, class ... args>
    constexpr int type_index(std::enable_if_t<!std::is_same_v<ty, arg>, int> = 0)
    {
        return 1 + type_index<ty, args ...>();
    }

    template <class ty, class ... args>
    struct type_seq_is_at_end
    {
        static constexpr int idx = type_index<ty, args ...>();
        static constexpr int size = types_size<args ...>();
        static constexpr bool value = idx == size - 1;
    };
    template <class ty, class ... args>
    constexpr bool types_is_at_end_v = type_seq_is_at_end<ty, args ...>::value;

    // get type by index
    template<size_t i, class ... types>
    struct get_type
    {};
    template<class ty, class ... types>
    struct get_type<0, ty, types ...>
    {
        using type = ty;
    };
    template<size_t i, class ty, class ... types>
    struct get_type<i, ty, types ...>
    {
        using type = typename get_type<i - 1, types ...>::type;
    };

    template<size_t i, class ... types>
    using get_type_t = typename get_type<i, types ...>::type;

    template <size_t i, class ... arg_types>
    struct get_arg
    {};

    template <class arg_type, class ... arg_types>
    struct get_arg<0, arg_type, arg_types ...>
    {
        arg_type operator ()(arg_type &&arg, arg_types&& ...)
        {
            return std::forward<arg_type>(arg);
        }
    };

    template <size_t i, class ... arg_types>
    get_type_t<i, arg_types ...> get_type_v = get_arg<i, arg_types>{};
}