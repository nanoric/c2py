import sys
import os
import traceback

import binding


def test():
    # cross_assign
    assert binding.attr == 1234
    assert binding.attr2 == 1234

    # c_function_callback
    def myfunc(val):
        return val
    binding.func_1(1, myfunc)
    binding.func_4(1,2,2,2,myfunc, 3,3)

    # array
    A = binding.A
    a: object = A()

    def write_then_read_test(attr_name, arr):
        a.__setattr__(attr_name, arr)
        assert a.__getattribute__(attr_name)[:len(arr)] == arr

    write_then_read_test("arr", [i for i in range(5)])
    write_then_read_test("arr", [i for i in range(9)])
    write_then_read_test("arr", [0 for _ in range(10)])
    write_then_read_test("arr", [i for i in range(len(a.arr))])

    write_then_read_test("double_arr", [[i+j*10 for i in range(10)] for j in range(10)])
    write_then_read_test("multi_arr", [[[i+j*10+k*100 for i in range(10)] for j in range(10)] for k in range(10)])



try:
    test()
    print("succeed")
except AssertionError as e:
    print("failed")
    traceback.print_exception(*sys.exc_info())
