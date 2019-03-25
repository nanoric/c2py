from unittest import TestCase, main

from autocxxpy.core import CXXParser
from autocxxpy.core.cxxparser import CXXParserExtraOptions, Arch


class ConstantType(TestCase):

    def test_32(self):
        src = """
        #ifdef _WIN64
        const int a = 64;
        #else
        const int a = 32;
        #endif
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
        a = result.g.variables['a']
        self.assertEqual(int, type(a.value))
        self.assertEqual(32, a.value)

    def test_64(self):
        src = """
        #ifdef _WIN64
        const int a = 64;
        #else
        const int a = 32;
        #endif
        """
        extra_options = CXXParserExtraOptions()
        extra_options.arch = Arch.X64
        unsaved_files = [
            ("./test.cpp", src)
        ]
        parser = CXXParser("./test.cpp",
                           unsaved_files,
                           extra_options=extra_options,
                           )
        result = parser.parse()
        a = result.g.variables['a']
        self.assertEqual(int, type(a.value))
        self.assertEqual(64, a.value)


if __name__ == '__main__':
    main()