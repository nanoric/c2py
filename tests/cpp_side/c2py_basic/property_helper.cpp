#include <c2py/property_helper.hpp>
#include <gtest/gtest.h>

namespace c2py
{
    namespace internal
    {
        // normal type
        static_assert(std::is_same_v<
            assign_value_type_t<int>,
            int
        >);

        // array
        static_assert(std::is_same_v<
            assign_value_type_t<int[3]>,
            std::vector<int>
        >);

        // nested array
        static_assert(std::is_same_v <
            assign_value_type_t<int[3][3]>,
            std::vector < std::vector<int> >
        >);

        // multi nested array
        static_assert(std::is_same_v <
            assign_value_type_t<int[3][3][3]>,
            std::vector < std::vector<std::vector<int>> >
        >);
    }
}



struct tag {};
class A
{
public:
    int normal;
    int arr[10];
    int double_arr[10][10];
    int multil_arr[10][10][10];
    int* pointer;
};
class property_getter_test : public ::testing::Test {
public:
    A a;
};

#define fori(i, name) for (int (i) = 0; (i) < sizeof(name) / sizeof(name[0]) ; (i)++)
TEST_F(property_getter_test, get_normal)
{
    using namespace c2py;
    auto normal = default_getter_wrap<tag>(&A::normal);

    a.normal = 1;
    {
        EXPECT_EQ(normal(a), 1);
    }
}
TEST_F(property_getter_test, get_arr)
{
    using namespace c2py;
    auto arr = default_getter_wrap<tag>(&A::arr);

    int n = 0;
    fori(i, a.arr)
    {
        a.arr[i] = n++;
    }

    n = 0;
    auto res = arr(a);
    for (auto i : res)
    {
        EXPECT_EQ(*i, n++);
    }
}

TEST_F(property_getter_test, get_double_arr)
{
    using namespace c2py;

    auto double_arr = default_getter_wrap<tag>(&A::double_arr);
    int n = 0;
    fori(i, a.double_arr)
    {
        fori(j, a.double_arr[i])
        {
            a.double_arr[i][j] = n++;

        }
    }


    n = 0;
    auto res = double_arr(a);
    for (auto i : res)
    {
        for (auto j : *i)
        {
            EXPECT_EQ(j, n++);
        }
    }
}

//TEST_F(property_getter_test, get_multi_arr)
//{
//    using namespace c2py;
//    auto multi_arr = default_getter_wrap<tag>(&A::multil_arr);
//    int n = 0;
//    fori(i, a.multil_arr)
//    {
//        fori(j, a.multil_arr[i])
//        {
//            fori(k, a.multil_arr[i][j])
//            {
//                a.multil_arr[i][j][k] = n++;
//            }
//        }
//    }
//
//    n = 0;
//    auto res = multi_arr(a);
//    //for (auto i : res)
//    //{
//    //    for (auto j : i)
//    //    {
//    //        for (auto k: *j)
//    //        {
//    //            EXPECT_EQ(k, n++);
//    //        }
//    //    }
//    //}
//}


TEST_F(property_getter_test, get_pointer_arr)
{
    using namespace c2py;
    auto pointer = default_getter_wrap<tag>(&A::pointer);
    int n = 33;
    a.pointer = &n;

    EXPECT_EQ(*pointer(a), n);
}
