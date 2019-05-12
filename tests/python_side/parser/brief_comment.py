from unittest import TestCase, main

from autocxxpy.core import CXXParser


class BriefComment(TestCase):

    def test_variable_short_brief_comment(self):
        src = """
        //! ss
        int short_ = 1;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        short = result.g.variables['short_']
        self.assertEqual("ss", short.brief_comment)

    def test_variable_long_brief_comment(self):
        src = """
        /*!
         * abcd
         */
        int long_ = 1;
        """
        parser = CXXParser("./test.cpp", [
            ("./test.cpp", src)
        ])
        result = parser.parse()
        long = result.g.variables['long_']
        self.assertEqual("abcd", long.brief_comment)


if __name__ == "__main__":
    main()
