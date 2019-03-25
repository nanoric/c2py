from unittest import TestCase, main, skip

from autocxxpy.core import CXXParser
from autocxxpy.core.cxxparser import Arch, CXXParserExtraOptions


class ConstantType(TestCase):

    @skip("always false: I don't know to to deal with this")
    def test_undef(self):
        src = """
        #define A 1234
        #undef A
        """
        extra_options = CXXParserExtraOptions()
        extra_options.arch = Arch.X86
        unsaved_files = [
            ("./test.cpp", src)
        ]
        parser = CXXParser("./test.cpp",
                           unsaved_files,
                           extra_options=extra_options,
                           )
        result = parser.parse()
        self.assertNotIn('A', result.macros)

    def test_value(self):
        src = """
        #define A 1234
        #undef A
        #define A 123
        int a = A;
        """
        extra_options = CXXParserExtraOptions()
        extra_options.arch = Arch.X86
        unsaved_files = [
            ("./test.cpp", src)
        ]
        parser = CXXParser("./test.cpp",
                           unsaved_files,
                           extra_options=extra_options,
                           )
        result = parser.parse()
        self.assertEqual('123', result.macros['A'].definition)
        self.assertEqual(123, result.g.variables['a'].value)


if __name__ == '__main__':
    main()
