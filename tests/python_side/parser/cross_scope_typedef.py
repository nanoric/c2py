from unittest import TestCase, main

from autocxxpy.parser import CXXParser


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
        ns1 = result.namespaces['ns1']
        self.assertIn("int32", ns1.typedefs)
        self.assertEqual("int", ns1.typedefs['int32'].target)

        ns2 = result.namespaces['ns2']
        self.assertIn("int32", ns2.typedefs)
        self.assertEqual("::ns1::int32", ns2.typedefs['int32'].target)


if __name__ == "__main__":
    main()
