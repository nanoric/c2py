#include <iostream>

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <c2py/c2py.hpp>
#include <c2py/base/type.h>
#include <c2py/wrappers/output_argument.hpp>


using namespace c2py;

using ft = std::function<void()>;
ft f;
void set_raise_func(const ft& f)
{
    ::f = f;
}

void async_call()
{
    f();
}

struct A
{
    void abs_func()
    {
        callback_wrapper<&A::abs_func>::async(this, "abs_func");
    }
    void make_call()
    {
        abs_func();
    }
};

PYBIND11_MODULE(exception_handling, m)
{
    // async dispatcher exception handler
    {
        m.def("set_async_callback_exception_handler", &c2py::async_callback_exception_handler::set_handler);
        pybind11::class_<c2py::async_dispatch_exception> c(m, "AsyncDispatchException");
        c.def_property("what", &async_dispatch_exception::what, nullptr);
        c.def_readonly("instance", &async_dispatch_exception::instance);
        c.def_readonly("function_name", &async_dispatch_exception::function_name);
    }


    // dipatcher
    c2py::dispatcher::instance().start();

    m.def("set_raise_func", &set_raise_func);
    pybind11::class_<A> c(m, "A");
    c.def(pybind11::init<>());
    c.def("make_call", &A::make_call);
}