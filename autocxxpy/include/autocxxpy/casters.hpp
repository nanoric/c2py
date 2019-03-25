#pragma once

#include <memory>
#include <string>
#include "config/config.hpp"

#include <pybind11/pybind11.h>

namespace autocxxpy
{
    struct caster
    {
        template <class T>
        inline static std::unique_ptr<T> copy(void *ptr)
        {
            return std::make_unique<T>(*(T *)ptr);
        }

        template <class T>
        inline static T *reinterpret(void *ptr)
        {
            return (T *)ptr;
        }

        static char *toString(void *ptr)
        {
            return reinterpret<char>(ptr);
        }
        static std::string tostr(void *ptr)
        {
            return (char *)ptr;
        }
        //static void *allocate(int size)
        //{
        //    auto p = new char[size];
        //    memset(p, 0, size);
        //    return p;
        //}
        //static void free(void *ptr)
        //{
        //    delete ptr;
        //}
#ifdef AUTOCXXPY_INCLUDED_PYBIND11
        template <class T>
        static auto bind(T &m, const char *name = "caster")
        {
            pybind11::class_<caster> c(m, name);
            c.def("tostring", &toString);
            c.def("tostr", &tostr);
            return c;
        }

        template <class to_type, class scope_type>
        static auto generate(scope_type &m, const char *name)
        {
            if constexpr (std::is_default_constructible_v<::ITapTrade::TapAPIApplicationInfo>){
                generate_nocheck<to_type>(m, name);
            }
        }
    private:
        template <class to_type, class scope_type>
        static auto generate_nocheck(scope_type &c, const char *name)
        {
            c.def("to_TapAPIApplicationInfo", 
                &autocxxpy::caster::copy<::ITapTrade::TapAPIApplicationInfo>
                );
        }
#endif
    };
}
