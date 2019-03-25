from unittest import TestCase, main

from autocxxpy.parser import CXXParser


class ConstantType(TestCase):

    def test_stl_optional(self):
        src = """
        #include <optional>
        std::optional<int> v = 1;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        v = result.variables['v']
        self.assertEqual("std::optional<int>", v.type)


if __name__ == "__main__":
    main()
