# 0.3.3: 
* New: generate setup.py

# 0.3:
important change:
* Change: global variable with type of 'char' in C/C++ will convert to 'str' instead of 'int' in python.  
  (Because we are using pybind11)
 
# 0.2.4: 
 New: brief_comment
    
# 0.2:
* New: command line interface(CLI)
* New: unsupported functions list
* New: added support for anonymous union
* New: CXXParse can now recognize some template, but not fully parsed.
* New: CXXParser can now parse namespace
* New: Added support for ```using alias = type```type;

* Removed: Removed GeneratorLiteralVariable, use GeneratorVariable instead
* Removed: Deleted export enum option: exports all non-scoped enum

# 0.1:
New: Global functions, enums, variables, classes, typedefs
New: PreProcessor recognize C style define

