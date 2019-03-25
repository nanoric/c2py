from unittest import TestCase, main, skip

from autocxxpy.parser import CXXParser


class NamespaceTest(TestCase):

    def test_nested_namespace(self):
        src = """
        namespace outer{
            namespace inner{
                class Inner1{};
            }
            class Outer1{};
            int namespace_func();
        };
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        self.assertIn("outer", result.namespaces)
        outer = result.namespaces['outer']
        self.assertIn("Outer1", outer.classes)
        self.assertIn("inner", outer.namespaces)

        inner = outer.namespaces['inner']
        self.assertIn("Inner1", inner.classes)

    def test_partial_namespace(self):
        src1 = """
        namespace ns1{
            class A{};
        };
        """
        src2 = """
        namespace ns1{
            class B{};
        };
        """
        parser = CXXParser("src.h", [
            ("src.h", '#include "1.h"\n#include "2.h"'),
            ("./1.h", src1),
            ("./2.h", src2),
        ])
        result = parser.parse()
        self.assertIn("ns1", result.namespaces)
        ns1 = result.namespaces['ns1']
        self.assertIn("A", ns1.classes)
        self.assertIn("B", ns1.classes)

    @skip("un supported currently")
    def test_using_namespace(self):
        src = """
        namespace ns1{
            class A{};
        };
        namespace ns2{
            using namespace ns1;
        }
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        self.assertIn("ns1", result.namespaces)
        ns1 = result.namespaces['ns1']
        self.assertIn("A", ns1.classes)

        self.assertIn("ns2", result.namespaces)
        ns2 = result.namespaces['ns2']
        self.assertIn("A", ns2.classes)

    @skip("un supported currently")
    def test_using_type(self):
        src = """
        namespace ns1{
            class A{};
        };
        namespace ns2{
            using ns1::A;
        }
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        self.assertIn("ns1", result.namespaces)
        ns1 = result.namespaces['ns1']
        self.assertIn("A", ns1.classes)

        self.assertIn("ns2", result.namespaces)
        ns2 = result.namespaces['ns2']
        self.assertIn("A", ns2.classes)


if __name__ == "__main__":
    main()
