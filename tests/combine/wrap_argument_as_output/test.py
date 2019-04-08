from wrap_argument_as_output import *

a = f()
assert a == 1
x, a , b = f2()
assert x == 1 and a == 11 and b == 12
x, a,b,c=f3()
assert x == 1 and a == 21 and b == 22 and c == 23
print("passed!")

exit(0)