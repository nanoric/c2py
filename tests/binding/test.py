import sys
import os
import traceback

import binding

def myfunc(a: int):
    print(a)
    return 1


try:
    binding.func(1, myfunc)
except:
    traceback.print_exception(*sys.exc_info())
    
try:
    binding.func2(1,2,2,2,myfunc, 3,3)
except:
    traceback.print_exception(*sys.exc_info())


import code
code.interact(local=locals())



