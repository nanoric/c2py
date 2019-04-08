from wrap_c_function_callback import *

val1 = False
val2 = False
val3 = [0, 0, 0]


def callback1():
    global val1
    val1 = True
    return 1


ret = f(callback1)
assert val1 == True and ret == 1


def callback2(a: int):
    global val2
    val2 = a
    return a + 100


ret = f2(123, callback2)
assert 123 == val2 and ret == 223


def callback3(a: int, b: int, c: int):
    global val3
    val3 = [a, b, c]
    return 456


ret = f3(1, callback3, 2, 3)
assert ret == 456 and val3 == [1, 2, 3]

print("passed!")

exit(0)
