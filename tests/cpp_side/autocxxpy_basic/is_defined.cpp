#include <autocxxpy/autocxxpy.hpp>
#include <autocxxpy/utils/type_traits.hpp>
#include <type_traits>

using namespace autocxxpy;

class A;
class B {};

static_assert(is_defined_v<A> == false);
static_assert(is_defined_v<B> == true);
static_assert(is_defined_v<void> == false);
static_assert(is_defined_v<int> == true);
