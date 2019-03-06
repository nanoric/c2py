#pragma once

namespace autocxxpy
{
    template <class element, size_t size>
    using literal_array = element[size];
}