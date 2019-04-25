from exception_handling import *
import time


run = False
handle = False

def handler(a):
    global handle
    handle = True
    print(a)
    print(dir(a))
    print(a.what)
    return True

set_async_callback_exception_handler(handler)

class B(A):
    def abs_func(self, ):
        global run
        run = True
        raise Exception("123")

b = B()
b.make_call()


time.sleep(1)
if handle and run:
    exit(0)
exit(1)
