from unittest import TestCase, main

from c2py.core import CXXParser


class ExternCTest(TestCase):

    def test_scoped_extern_c(self):
        src = """
        extern "C" {
            int c_function(int);
        }
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        self.assertIn('c_function', result.g.functions)
        pass

    def test_extern_c(self):
        src = """
        extern "C" int c_function(int);
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        self.assertIn('c_function', result.g.functions)
        pass


if __name__ == "__main__":
    main()
