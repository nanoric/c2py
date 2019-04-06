#pragma once

#include "../../base/type.h"
#include "../../base/check.h"

#include <boost/callable_traits.hpp>
#include "../../brigand.hpp"

#ifdef AUTOCXXPY_INCLUDED_PYBIND11
#include <pybind11/stl.h>
#endif

namespace autocxxpy
{
	template <class T, class T2>
	auto append_as_tuple(T&& v1, T2& v2)
	{
		return std::forward_as_tuple<T, T2>(std::move(v1), std::forward<T2>(v2));
	}

	template <class ... Ts, class T2, size_t ... idx>
	auto append_as_tuple_impl(std::tuple<Ts...> tv, T2& v2, std::index_sequence<idx...>)
	{
		return std::forward_as_tuple<Ts ..., T2>(std::get<idx>(tv) ..., v2);
	}

	template <class ... Ts, class T2>
	auto append_as_tuple(std::tuple<Ts& ...>&& tv, T2& v2)
	{
		return append_as_tuple_impl(tv, v2, std::index_sequence_for<Ts...>{});
	}

	template <class MethodConstant, class base_t, class ... Ls, class ... Rs>
	inline constexpr auto wrap_pointer_argument_as_output_impl(brigand::list<Ls...>, brigand::list <Rs...>)
	{
		namespace ct = boost::callable_traits;
		return [](Ls ... ls, Rs ... rs)
		{
			base_t arg;
			constexpr auto method = MethodConstant::value;
			using ret_t = typename ct::return_type<decltype(method)>::type;
			if constexpr (std::is_void_v<ret_t>)
			{
				method(ls ..., &arg, rs ...);
				return arg;
			}
			else
			{
				return append_as_tuple(method(
					ls...,
					&arg,
					rs...
				), arg);
			}
		};
	}

	template <class MethodConstant, size_t index>
	inline constexpr auto wrap_argument_as_output()
	{
		using namespace brigand;
		namespace ct = boost::callable_traits;

		constexpr auto method = MethodConstant::value;
		using func_t = ct::function_type_t<decltype(method)>;
		using args_t = wrap<ct::args_t<func_t>, list>;

		if constexpr (check_not_out_of_bound<index, sizeof_<args_t>::value>())
		{
			using s = split_at<args_t, std::integral_constant<int, index>>;
			using ls = front<s>;
			using rs = pop_front<back<s>>;
			using arg_t = at<args_t, std::integral_constant<int, index>>;

			if constexpr (std::is_pointer_v<arg_t>)
			{
				using base_t = std::remove_pointer_t<arg_t>;
				return wrap_pointer_argument_as_output_impl<MethodConstant, base_t>(ls{}, rs{});
			}
			else
			{
				using base_t = std::remove_reference_t<arg_t>;
				// todo: implement this.
				//static_assert(std::is_reference, "not implemented");
			}
		}
	}

	template <class MethodConstant, size_t index>
	struct output_argument_transform
	{
		using type = output_argument_transform;
		using value_type = decltype(wrap_argument_as_output<MethodConstant, index>());
		static constexpr value_type value = wrap_argument_as_output<MethodConstant, index>();
	};

	template <class MethodConstant, class IntegralConstant>
	struct output_argument_transform2 : output_argument_transform<MethodConstant, IntegralConstant::value>
	{};
}
