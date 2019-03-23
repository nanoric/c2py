from unittest import TestCase, main

from autocxxpy.parser import CXXParser


class ExternCTest(TestCase):

    def test_extern_c(self):
        src = """
        extern "C" {
            int c_function(int);
        }
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        self.assertIn('c_function', result.functions)
        pass


if __name__ == "__main__":
    main()
