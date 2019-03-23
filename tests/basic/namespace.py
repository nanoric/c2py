from unittest import TestCase, main

from autocxxpy.parser import CXXParser


class NamespaceTest(TestCase):

    def test_nested_namespace(self):
        src = """
        namespace outer{
            namespace inner{
            class Inner1{};
            class Inner2{};
            }
            class Outer1{
                class EmbedClass {
                    int method();
                };
                int method();
            };
            class Outer2{};
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
        self.assertIn("Outer2", outer.classes)
        self.assertIn("inner", outer.namespaces)

        inner = outer.namespaces['inner']
        self.assertIn("Inner1", inner.classes)
        self.assertIn("Inner2", inner.classes)
        pass


if __name__ == "__main__":
    main()
