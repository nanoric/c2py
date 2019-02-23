#pragma once

namespace autocxxpy
{
    template< class T >
    struct remove_cvref { using type = std::remove_cv_t<std::remove_reference_t<T>>; };

    template< class T >
    using remove_cvref_t = typename remove_cvref<T>::type;

    template <class ty, template <class...> class base>
    struct is_specialization_of_impl :std::false_type {};

    template <template <class...> class base, class... args>
    struct is_specialization_of_impl<base<args...>, base> : std::true_type {};

    //! Tests if ty is a specialization of ty
    template <class ty, template <class...> class base>
    struct is_specialization_of : is_specialization_of_impl<typename remove_cvref<ty>::type, base> {};

    template <class ty, template <class...> class base>
    constexpr bool is_specialization_of_v = is_specialization_of<ty, base>::value;
}
