from unittest import TestCase, main

from c2py.core import CXXParser
from c2py.core.core_types.parser_types import AnonymousUnion
from c2py.core.cxxparser import CXXParserExtraOptions, Arch


class ConstantType(TestCase):

    def test_union(self):
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

        # U in C
        C = result.g.classes['C']
        self.assertIn("s", C.variables)
        self.assertIn('U', C.classes)
        self.assertNotIn('a', C.variables)

        # a in s
        U = C.classes['U']
        self.assertIn('a', U.variables)

        a = U.variables['a']

        # limits
        self.assertEqual(1, len(C.classes))
        self.assertEqual(1, len(C.variables))
        self.assertEqual(0, len(U.classes))
        self.assertEqual(1, len(U.variables))

        # objects
        self.assertEqual(C, result.objects['C'])
        self.assertEqual(U, result.objects['C::U'])
        self.assertEqual(a, result.objects['C::U::a'])

    def test_union_unscoped(self):
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

        # U in C
        result = parser.parse()
        C = result.g.classes['C']
        self.assertIn("U", C.classes)

        # a in C
        self.assertIn("a", C.variables)

        # a in U
        U = C.classes['U']
        self.assertIn('a', U.variables)

        a = U.variables['a']

        # limits
        self.assertEqual(1, len(C.classes))
        self.assertEqual(1, len(C.variables))
        self.assertEqual(0, len(U.classes))
        self.assertEqual(1, len(U.variables))

        # objects
        self.assertEqual(C, result.objects['C'])
        self.assertEqual(U, result.objects['C::U'])
        self.assertEqual(a, result.objects['C::U::a'])

    def test_union_anonymous_scoped(self):
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

        # s in C
        C = result.g.classes['C']
        self.assertIn("s", C.variables)
        self.assertNotIn("a", C.variables)

        # a in s
        typeof_s = C.classes['decltype(s)']
        self.assertIsInstance(typeof_s, AnonymousUnion)
        self.assertIn('a', typeof_s.variables)

        a = typeof_s.variables['a']

        # limits
        self.assertEqual(1, len(C.classes))  # one anonymous class
        self.assertEqual(1, len(C.variables))
        self.assertEqual(0, len(typeof_s.classes))
        self.assertEqual(1, len(typeof_s.variables))

        # objects
        self.assertEqual(C, result.objects['C'])
        self.assertEqual(typeof_s, result.objects['decltype(C::s)'])
        self.assertEqual(a, result.objects['decltype(C::s)::a'])

    def test_union_anonymous_unscoped(self):
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

        # a in C
        C = result.g.classes['C']
        self.assertIn("a", C.variables)
        a = C.variables['a']

        # limits
        self.assertEqual(0, len(C.classes))
        self.assertEqual(1, len(C.variables))

        # objects
        self.assertEqual(C, result.objects['C'])
        self.assertEqual(a, result.objects['C::a'])


if __name__ == '__main__':
    main()