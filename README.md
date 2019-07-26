# c2py

This tool is used for generate Source Files for C/C++ Extensions(.pyd files) from C/C++ headers.

## Different with other tools:

If you want to use C/C++ code in python. In the past, you have two options:
 * ```ctypes```
 * Writing C Extension with ```boost.python``` or ```pybind11``` or some other libraries.

In both ways, you must write your own code to generate a C Extension(.pyd file).
Writing your own code require that you are experienced in C/C++ 
and **TAKES A LONG TIME** to coding.

------

With c2py you don't need to be so experienced in C/C++.
It will try its best to help you 
resolve all the problem you might face 
when generating a binding from C/C++ to python.

All you need(in ideal situation), is just run c2py and then, build.

## Project goal
We hope people can use any C/C++ code by just run c2py & build,
leaving all the trouble to c2py.

## Features:
 * to produce a pyd file(or its source) instead of just providing a binding library.
 * handles almost all the trouble you may face when writing your own code.
 * fully typed type hint files(.pyi files).
 * generated pyd has a identical layout as C++ namespace.
 * recognize almost everything in C++.(See [TODO.txt](./TODO.txt) for a full list.)
 * recognize constant declared by #define. (people writing C likes this)
 * Functions, class method, getters & setters can be customized using C++ template specialization
  if c2py is not good enough.(Wish you contribute your code to c2py instead of writing your own private solution)

## install
```bash
pip install https://github.com/nanoric/c2py/archive/master.zip
```

## Usage
```text
> c2py --help
Usage: c2py [OPTIONS] MODULE_NAME [FILES]...

  Converts C/C++ .h files into python module source files. All matching is
  based on c++ qualified name, using regex.

Options:
  -e, --encoding TEXT             encoding of input files, default is utf-8
  -I, --include-path TEXT         additional include paths
  -A, --additional-include TEXT   additional include files. These files will
                                  be included in output cxx file, but skipped
                                  by parser.
  -ew, --string-encoding-windows TEXT
                                  encoding used to get & set string. This
                                  value is used to construct std::locale. use
                                  `locale -a` to show all the locates
                                  supported. default is utf-8, which is the
                                  internal encoding used by pybind11.
  -el, --string-encoding-linux TEXT
                                  encoding used to get & set string. This
                                  value is used to construct std::locale. use
                                  `locale -a` to show all the locates
                                  supported. default is utf-8, which is the
                                  internal encoding used by pybind11.
  -i, --ignore-pattern TEXT       ignore symbols matched
  --no-callback-pattern TEXT      disable generation of callback for functions
                                  matched (for some virtual method used as
                                  undocumented API)
  --no-transform-pattern TEXT     disable applying transforms(changing its
                                  signature) into functions matched (for some
                                  virtual method used as callback only)
  --inout-arg-pattern TEXT        make symbol(arguments only) as input_output
  --output-arg-pattern TEXT       make symbol(arguments only) as output only
  --m2c / --no-m2c                treat const macros as global variable
  --ignore-underline-prefixed / --no-ignore-underline-prefixed
                                  ignore global variables starts with
                                  underline
  --ignore-unsupported / --no-ignore-unsupported
                                  ignore functions that has unsupported
                                  argument
  -o, --output-dir PATH           module source output directory
  -p, --pyi-output-dir PATH       pyi files output directory
  --clear-output-dir / --no-clear-output-dir
  --clear-pyi-output-dir / --no-clear-pyi-output-dir
  --copy-c2py-includes TEXT  copy all c2py include files, excluding
                                  input files to specific dir.
  -m, --max-lines-per-file INTEGER RANGE
  --generate-setup TEXT           if set, generate setup.py into this location
  --setup-lib-dir TEXT
  --setup-lib TEXT
  --setup-use-patches / --setup-no-use-patches
  --help                          Show this message and exit.

```

## Example
Just generate & run generated ```setup.py```: 
```bash
c2py vnctp                                         \
    ThostFtdcMdApi.h                                    \
    ThostFtdcTraderApi.h                                \
    ThostFtdcUserApiDataType.h                          \
    ThostFtdcUserApiStruct.h                            \
    -I                          vnctp/include/          \
    --no-callback-pattern       ".*Api::.*"             \
    --string-encoding-windows   .936                    \
    --string-encoding-linux     zh_CN.GB18030           \
                                                        \
    --copy-c2py-includes   vnctp/include/          \
    --output-dir                vnctp/generated_files/  \
    --clear-output-dir                                  \
                                                        \
    --generate-setup            .                       \
    --setup-lib-dir             vnctp/libs/             \
    --setup-lib                 thostmduserapi          \
    --setup-lib                 thosttraderapi

python ./setpu.py build
```
