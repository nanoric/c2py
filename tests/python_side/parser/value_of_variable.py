from unittest import TestCase, main

from autocxxpy.parser import CXXParser


class ConstantType(TestCase):

    def test_int(self):
        src = """
        const int a = 1;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        self.assertEqual(int, type(a.value))
        self.assertEqual(1, a.value)

    def test_float(self):
        src = """
        const float a = 1.0;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        self.assertEqual(float, type(a.value))
        self.assertEqual(1.0, a.value)

    def test_int_as_float(self):
        src = """
        const float a = 1;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        self.assertEqual(int, type(a.value))
        self.assertEqual(1, a.value)

    def test_float_as_int(self):
        src = """
        const int a = 1.0;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        self.assertEqual(float, type(a.value))
        self.assertEqual(1.0, a.value)

    def test_define(self):
        src = """
        #define N 2
        const int a = N;
        #define M 3
        const int b = M;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        b = result.variables['b']
        self.assertEqual(2, a.value)
        self.assertEqual(3, b.value)

    def test_double(self):
        src = """
        const double a = 1.0;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        self.assertEqual(float, type(a.value))
        self.assertEqual(1.0, a.value)

    def test_prefix(self):
        src = """
        const int a = 0x01;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        self.assertEqual(int, type(a.value))
        self.assertEqual(1, a.value)

    def test_suffix(self):
        src = """
        const int a = 1l;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        self.assertEqual(int, type(a.value))
        self.assertEqual(1, a.value)

    def test_prefix_and_suffix(self):
        src = """
        const int a = 0x01l;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        a = result.variables['a']
        self.assertEqual(int, type(a.value))
        self.assertEqual(1, a.value)


if __name__ == "__main__":
    main()
