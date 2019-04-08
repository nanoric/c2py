from unittest import TestCase, main

from autocxxpy.core import CXXParser
from autocxxpy.core.cxxparser import CXXParserExtraOptions, Arch


class ConstantType(TestCase):

    def test_named_union_all_named(self):
        src = """
        struct C{
            union U{
                int a;
            }s;
        };
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        C = result.g.classes['C']
        self.assertIn("s", C.variables)
        self.assertIn('U', C.classes)

        U = C.classes['U']
        self.assertIn('a', U.variables)

    def test_union_no_typename_named(self):
        src = """
        struct C{
            union {
                int a;
            }s;
        };
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        C = result.g.classes['C']
        self.assertIn("s", C.variables)

    def test_union_no_typename_anonymous(self):
        src = """
        struct C{
            union {
                int a;
            };
        };
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        C = result.g.classes['C']
        self.assertIn("a", C.variables)

    def test_union_has_typename_anonymous(self):
        src = """
        struct C{
            union U{
                int a;
            };
        };
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        C = result.g.classes['C']
        self.assertIn("U", C.classes)

        U = C.classes['U']
        self.assertIn('a', U.variables)


if __name__ == '__main__':
    main()