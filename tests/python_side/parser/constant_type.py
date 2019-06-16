from unittest import TestCase, main

from autocxxpy.core import CXXParser
from autocxxpy.core.core_types.cxx_types import is_const_type


class ConstantType(TestCase):

    def test_global_const(self):
        src = """
        const int a = 1;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.g.variables['a']
        self.assertTrue(a.const)

    def test_nested_const(self):
        src = """
        struct S{
            const int a = 1;
        };
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        s = result.g.classes['S']
        a = s.variables['a']
        self.assertTrue(is_const_type(a.type))
        self.assertTrue(a.const)

    def test_pointer_to_const(self):
        src = """
        const char *a = "";
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.g.variables['a']
        self.assertFalse(a.const)

    def test_const_pointer(self):
        src = """
        char * const a = "";
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.g.variables['a']
        self.assertTrue(is_const_type(a.type))
        self.assertTrue(a.const)

    def test_const_multiple_level_pointer(self):
        src = """
        #define N 0
        char ** const a = N;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.g.variables['a']
        self.assertTrue(is_const_type(a.type))
        self.assertTrue(a.const)

    def test_constexpr(self):
        src = """
        constexpr int a = 2;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.g.variables['a']
        self.assertTrue(a.const)

    def test_static_const(self):
        src = """
        static constexpr int a = 2;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.g.variables['a']
        self.assertTrue(a.const)


if __name__ == "__main__":
    main()
