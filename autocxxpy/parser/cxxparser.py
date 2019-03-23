import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from autocxxpy.clang.cindex import (
    Config,
    Cursor,
    CursorKind,
    Index,
    Token,
    TranslationUnit,
)
from autocxxpy.parser.cxxparser_types import Class, Enum, Function, Method, Namespace, Variable
from autocxxpy.parser.type import is_const
from autocxxpy.parser.utils import _try_parse_cpp_digit_literal

logger = logging.getLogger(__file__)
logging.basicConfig(level=logging.INFO)

internal_path_flag = \
    ['Tools\\MSVC',
     'Windows Kits']


def is_internal_file(path: str):
    for flag in internal_path_flag:
        if flag in path:
            return True
    return False


@dataclass()
class CXXParseResult(Namespace):
    macros: Dict[str, str] = field(default_factory=dict)


class CXXParser:

    def __init__(
        self,
        file_path: Optional[str],
        unsaved_files: Sequence[Sequence[str]] = None,
        args: List[str] = None,
    ):
        if args is None:
            args = []
        self.unsaved_files = unsaved_files
        self.file_path = file_path
        self.args = args
        if "-std=c++11" not in self.args:
            self.args.append("-std=c++11")
        self.unnamed_index = 0

        self.cursors: Dict = {}

    def parse(self) -> CXXParseResult:
        idx = Index.create()
        rs = idx.parse(
            self.file_path,
            args=self.args,
            unsaved_files=self.unsaved_files,
            options=(
                TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD |
                TranslationUnit.PARSE_SKIP_FUNCTION_BODIES |  # important
                TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION
            ),
        )
        ns = Namespace()
        self._process_namespace(rs.cursor, ns)
        result = CXXParseResult(**ns.__dict__)

        for ac in rs.cursor.walk_preorder():
            if ac.kind == CursorKind.MACRO_DEFINITION:
                name, definition = CXXParser._process_macro_definition(ac)
                result.macros[name] = definition
        return result

    def _process_namespace(self, c: Cursor, n: Namespace):
        """All result will append in parameter n"""
        if c.kind == CursorKind.NAMESPACE:
            n.name = c.spelling
        for ac in c.get_children():
            if ac.extent.start.file and is_internal_file(ac.extent.start.file.name):
                continue
            elif ac.kind == CursorKind.UNEXPOSED_DECL:
                self._process_namespace(ac, n)
            elif ac.kind == CursorKind.NAMESPACE:
                ns = Namespace()
                self._process_namespace(ac, ns)
                n.namespaces[ns.name] = ns
            elif ac.kind == CursorKind.FUNCTION_DECL:
                func = CXXParser._process_function(ac)
                n.functions[func.name].append(func)
            elif ac.kind == CursorKind.ENUM_DECL:
                e = CXXParser._process_enum(ac)
                n.enums[e.name] = e
            elif (
                ac.kind == CursorKind.CLASS_DECL or
                ac.kind == CursorKind.STRUCT_DECL or
                ac.kind == CursorKind.UNION_DECL
            ):
                class_ = self._process_class(ac)
                cname = class_.name
                n.classes[cname] = class_
                pass
            elif ac.kind == CursorKind.VAR_DECL:
                name, value = CXXParser._process_variable(ac)
                if value:
                    n.variables[name] = value
            elif ac.kind == CursorKind.TYPEDEF_DECL:
                name, target = CXXParser._process_typedef(ac)
                if name != target:
                    n.typedefs[name] = target
            elif (
                False or
                ac.kind == CursorKind.ENUM_CONSTANT_DECL or
                ac.kind == CursorKind.CXX_METHOD or
                ac.kind == CursorKind.CXX_FINAL_ATTR or
                ac.kind == CursorKind.DESTRUCTOR or
                ac.kind == CursorKind.PARM_DECL or
                ac.kind == CursorKind.CXX_ACCESS_SPEC_DECL or
                ac.kind == CursorKind.CONSTRUCTOR or
                ac.kind == CursorKind.FIELD_DECL
            ):
                # processed by other functions as child cursor
                pass
            elif ac.kind == CursorKind.COMPOUND_STMT:
                # ignore any body
                pass
            elif (
                CXXParser._is_literal_cursor(ac) or
                ac.kind == CursorKind.MACRO_INSTANTIATION or
                ac.kind == CursorKind.PAREN_EXPR or
                ac.kind == CursorKind.BINARY_OPERATOR or
                ac.kind == CursorKind.UNARY_OPERATOR or
                ac.kind == CursorKind.DLLIMPORT_ATTR or
                ac.kind == CursorKind.NAMESPACE_REF or
                ac.kind == CursorKind.INCLUSION_DIRECTIVE
            ):
                # just not need to parse
                pass
            elif (
                ac.kind == CursorKind.UNEXPOSED_DECL or  # extern "C"
                ac.kind == CursorKind.TYPE_REF or
                ac.kind == CursorKind.UNEXPOSED_EXPR or
                ac.kind == CursorKind.DECL_REF_EXPR
            ):
                # i don't know what those are
                pass
            else:
                if ac.extent.start.file:
                    logging.warning(
                        "unrecognized cursor kind: %s, %s, %s",
                        ac.kind,
                        ac.spelling,
                        ac.extent,
                    )
        return n

    @staticmethod
    def _process_function(c: Cursor):
        func = Function(
            name=c.spelling,
            ret_type=c.result_type.spelling,
            args=[
                Variable(name=ac.spelling, type=ac.type.spelling)
                for ac in c.get_arguments()
            ],
        )
        return func

    @staticmethod
    def _process_method(c: Cursor, class_):
        func = Method(
            parent=class_,
            name=c.spelling,
            ret_type=c.result_type.spelling,
            access=c.access_specifier.name.lower(),
            is_virtual=c.is_virtual_method(),
            is_pure_virtual=c.is_pure_virtual_method(),
            is_static=c.is_static_method(),
        )
        for ac in c.get_arguments():
            arg = Variable(ac.spelling, ac.type.spelling)
            func.args.append(arg)
        for ac in c.get_children():
            if ac.kind == CursorKind.CXX_FINAL_ATTR:
                func.is_final = True
            elif ac.kind == CursorKind.COMPOUND_STMT:
                # we don't care about the function body
                pass
            elif (ac.kind == CursorKind.TYPE_REF
                  or ac.kind == CursorKind.PARM_DECL
                  or ac.kind == CursorKind.NAMESPACE_REF):
                pass
            else:
                logger.warning(
                    "unknown kind in cxx_method child: %s %s",
                    ac.kind,
                    ac.extent,
                )
        return func

    def _process_class(self, c: Cursor):
        # noinspection PyArgumentList
        name = c.spelling
        class_ = Class(name=name)
        for ac in c.get_children():
            self._process_class_child(ac, class_)
        self.cursors[c.hash] = class_
        return class_

    def _process_class_child(self, c: Cursor, class_):
        if c.kind == CursorKind.CONSTRUCTOR:
            func = CXXParser._process_method(c, class_)
            if func.is_virtual:
                class_.is_polymorphic = True
            class_.constructors.append(func)
        elif (c.kind == CursorKind.CLASS_DECL or
              c.kind == CursorKind.STRUCT_DECL):
            child = self._process_class(c)
            class_.classes[child.name] = child
        elif c.kind == CursorKind.DESTRUCTOR:
            func = CXXParser._process_method(c, class_)
            if func.is_virtual:
                class_.is_polymorphic = True
            class_.destructor = func
        elif c.kind == CursorKind.FIELD_DECL:
            v = Variable(c.spelling, c.type.spelling)
            class_.variables[v.name] = v
        elif c.kind == CursorKind.CXX_METHOD:
            func = CXXParser._process_method(c, class_)
            if func.is_virtual:
                class_.is_polymorphic = True
            class_.functions[func.name].append(func)
        elif c.kind == CursorKind.CXX_ACCESS_SPEC_DECL:
            pass
        elif c.kind == CursorKind.UNION_DECL:
            pass
        else:
            logger.warning(
                "unknown kind in class child, and not handled: %s %s",
                c.kind,
                c.extent,
            )

    @staticmethod
    def _process_enum(c: Cursor):
        e = Enum(name=c.spelling, type=c.enum_type.spelling)
        for i in list(c.get_children()):
            e.values[i.spelling] = Variable(
                name=i.spelling, type=e.name, default=i.enum_value
            )
        return e

    @staticmethod
    def _process_variable(c: Cursor):
        children = list(c.walk_preorder())
        for child in children:
            if CXXParser._is_literal_cursor(child):
                value = CXXParser._parse_literal(child)
                var = Variable(
                    name=c.spelling,
                    type=c.type.spelling,
                    parent=None,
                    constant=is_const(c.type.spelling),
                    default=value,
                )
                return c.spelling, var

        logger.warning(
            "unable to parse variable : %s %s", c.spelling, c.extent
        )
        return c.spelling, None

    @staticmethod
    def _process_typedef(c: Cursor):
        target: str = c.underlying_typedef_type.spelling

        if target.startswith('struct '):
            target = target[7:]
        elif target.startswith('class '):
            target = target[6:]
        elif target.startswith('union '):
            target = target[6:]
        elif target.startswith('enum '):
            target = target[5:]
        name = c.spelling
        return name, target

    @staticmethod
    def _process_macro_definition(c: Cursor):
        name = c.spelling
        tokens = list(c.get_tokens())
        length = len(tokens)
        if length == 1:
            return name, ""
        return name, " ".join([i.spelling for i in tokens[1:]])

    @staticmethod
    def _get_source_from_file(file, start, end, encoding="utf-8"):
        with open(file, "rb") as f:
            f.seek(start)
            return f.read(end - start).decode(encoding=encoding)

    @staticmethod
    def _get_source(token: Token, encoding="utf-8"):
        return CXXParser._get_source_from_file(
            token.location.file.name,
            token.extent.start.offset,
            token.extent.end.offset,
            encoding,
        )

    LITERAL_KINDS = {
        CursorKind.INTEGER_LITERAL,
        CursorKind.STRING_LITERAL,
        CursorKind.CHARACTER_LITERAL,
        CursorKind.CXX_NULL_PTR_LITERAL_EXPR,
        CursorKind.FLOATING_LITERAL,
        CursorKind.IMAGINARY_LITERAL,
        CursorKind.CXX_BOOL_LITERAL_EXPR,
        # CursorKind.OBJC_STRING_LITERAL,
        # CursorKind.OBJ_BOOL_LITERAL_EXPR,
        # CursorKind.COMPOUND_LITERAL_EXPR,
    }

    @staticmethod
    def _is_literal_cursor(c: Cursor):
        return c.kind in CXXParser.LITERAL_KINDS
        # return str(c)[-9:-1] == 'LITERAL'

    @staticmethod
    def _parse_literal(c):
        tokens = list(c.get_tokens())
        if len(tokens) == 1:
            spelling = tokens[0].spelling
            if c.kind == CursorKind.INTEGER_LITERAL:
                return _try_parse_cpp_digit_literal(spelling).value
            elif c.kind == CursorKind.STRING_LITERAL:
                return str(spelling)
            elif c.kind == CursorKind.CHARACTER_LITERAL:
                return CXXParser.character_literal_to_int(spelling)
            elif c.kind == CursorKind.FLOATING_LITERAL:
                return float(spelling)
        logger.warning(
            "unknown literal : %s, %s %s", c.kind, c.spelling, c.extent
        )
        return None

    @staticmethod
    def character_literal_to_int(string):
        s = 0
        for i in string.encode():
            s = s * 255 + i
        return s

    pass


class CXXFileParser(CXXParser):

    def __init__(
        self,
        files: Sequence[str],
        include_paths: Sequence[str] = None,
        args: List[str] = None,
    ):
        if args is None:
            args = []
        if include_paths:
            for include_path in include_paths:
                args.append("-I" + include_path)
        dummy_code = ""
        for file in files:
            dummy_code += f'#include "{file}"\n'

        dummy_name = "dummy.cpp"

        super().__init__(
            dummy_name, unsaved_files=[
                [dummy_name, dummy_code],
            ], args=args
        )


mydir = os.path.split(os.path.abspath(__file__))[0]
template_dir = os.path.join(mydir, "templates")
include_dir = os.path.join(mydir, "include")
Config.set_library_path(os.path.join(mydir, "../", "clang"))
