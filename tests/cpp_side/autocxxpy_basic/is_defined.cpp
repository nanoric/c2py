#include <c2py/c2py.hpp>
#include <c2py/utils/type_traits.hpp>
#include <type_traits>

using namespace c2py;

class A;
class B {};

static_assert(is_defined_v<A> == false);
static_assert(is_defined_v<B> == true);
static_assert(is_defined_v<void> == false);
static_assert(is_defined_v<int> == true);
