#include <pybind11/pybind11.h>
#include <stdint.h>


template <class T>
auto make_capsule(T &val)
{
    return pybind11::capsule(new T(val), [](void *ptr) 
    {
        T *typed = (T *)ptr;
        delete typed;
    });
}

void init_capsule(pybind11::module &m, const char *name)
{
    m.def(name, &make_capsule<int64_t>);
    m.def(name, &make_capsule<uint64_t>);
    m.def(name, &make_capsule<double>);
}

