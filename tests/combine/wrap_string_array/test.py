from wrap_string_array import *

s1, s2 = f(["str1", "str2"])
assert s1 == "str1" and s2 == "str2"

s1, = prefix_all("prefix_", ["s1"])
assert s1 == "prefix_s1"

s1, s2, s3 = prefix_all("prefix_", ["s1", "s2", "s3"])
assert s1 == "prefix_s1"
assert s2 == "prefix_s2"
assert s3 == "prefix_s3"

s1, s2 = append_all(["s1", "s2"], "_suffix")
assert s1 == "s1_suffix"
assert s2 == "s2_suffix"

print("passed!")
exit(0)