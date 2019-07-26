from unittest import TestCase, main

from c2py.core import CXXParser


class CrossScopeTypedef(TestCase):

    def test_cross_scope_typedef(self):
        src = """
        namespace ns1{
            using int32 = int;
        };
        namespace ns2{
            using int32 = ns1::int32;
        }
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        ns1 = result.g.namespaces['ns1']
        self.assertIn("int32", ns1.typedefs)
        self.assertEqual("int", ns1.typedefs['int32'].target)

        ns2 = result.g.namespaces['ns2']
        self.assertIn("int32", ns2.typedefs)
        self.assertEqual("::ns1::int32", ns2.typedefs['int32'].target)

    def test_in_scope_type(self):
        src = """
        namespace ns1{
            using int32 = int;
            int32 a = 1;
        };
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        ns1 = result.g.namespaces['ns1']

        self.assertIn("a", ns1.variables)
        self.assertEqual("ns1::int32", ns1.variables['a'].type)


if __name__ == "__main__":
    main()
