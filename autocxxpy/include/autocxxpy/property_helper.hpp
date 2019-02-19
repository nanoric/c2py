#pragma once

#include <vector>
#include <functional>
#include <mutex>
#include <condition_variable>

#include <pybind11/pybind11.h>


namespace autocxxpy
{
    template <class class_type, class value_type>
    auto wrap_getter(value_type class_type::*member)
    {
        return [member](const class_type &instance)->const value_type & {
            return instance.*member;
        };
    }

    template <class class_type, class value_type>
    auto wrap_setter(value_type class_type::*member)
    {
        return [member](class_type &instance, const value_type &value) {
            instance.*member = value;
        };
    }

    // specialization for const setter
    template <class class_type, class value_type>
    auto wrap_setter(const value_type class_type::*member)
    { // match const
        return nullptr;
    }

    // specialization for any []
    template <class element_t, size_t size>
    using array_literal = element_t[size];

    template <class class_type, class element_t, size_t size>
    auto wrap_getter(array_literal<element_t, size> class_type::*member)
    { // match get any []
        return [member](const class_type &instance) {
            return instance.*member;
        };
    }

    template <class class_type, class element_t, size_t size>
    auto wrap_setter(array_literal<element_t, size> class_type::*member)
    { // match set any []
        return [member](class_type &instance, const std::vector<element_t> &value) {
            if (value.size() >= size)
            {
                auto s = std::string("Array too large, maximum size : ") + std::to_string(size) + " your size: " + std::to_string(value.size());
                throw std::runtime_error(s);
            }
            for (int i = 0; i < value.size(); i++)
            {
                (instance.*member)[i] = value.at(i);
            }
        };
    }

    // specialization for any *[]
    template <class class_type, class element_t, size_t size>
    auto wrap_getter(array_literal<element_t *, size> class_type::*member)
    { // match get (any *)[]
        return [member](const class_type &instance) {
            std::vector<element_t *> arr;
            for (auto &v : instance.*member)
            {
                arr.push_back(v);
            }
            return arr;
        };
    }

    // specialization for char[]
    template <size_t size>
    using string_literal = array_literal<char, size>;

    template <class class_type, size_t size>
    auto wrap_getter(string_literal<size> class_type::*member)
    { // match get char []
        return [member](const class_type &instance) {
            return instance.*member;
        };
    }


    template <class class_type, size_t size>
    auto wrap_setter(string_literal<size> class_type::*member)
    { // match set char []
        return [member](class_type &instance, const std::string_view &value) {
            strcpy(instance.*member, value.data());
        };
    }
}
#define AUTOCXXPY_DEF_PROPERTY(cls, name) \
		def_property(#name, autocxxpy::wrap_getter(&cls::name), autocxxpy::wrap_setter(&cls::name))
