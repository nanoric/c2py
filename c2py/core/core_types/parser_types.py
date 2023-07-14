from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass(repr=0)
class FileLocation:
    offset: int = 0
    line: int = 0
    column: int = 0


@dataclass(repr=False)
class Location:
    file: Optional[str] = None
    start: Optional[FileLocation] = None
    end: Optional[FileLocation] = None


@dataclass(repr=False)
class Symbol:
    name: str = ""
    parent: Optional["AnyCxxSymbol"] = None
    location: Location = None
    brief_comment: str = ""  # qt style brief comment : starts with /*! or //!

    @property
    def full_name(self):
        if self.parent is None or self.parent.full_name == "":
            return f"{self.name}"
        return f"{self.parent.full_name}::{self.name}"

    def __repr__(self):
        return f"{self.__class__.__name__}@{self.full_name}"


@dataclass(repr=False)
class Macro(Symbol):
    definition: str = ""


@dataclass(repr=False)
class Typedef(Symbol):
    target: str = ""


@dataclass(repr=False)
class Variable(Symbol):
    type: str = ""
    const: bool = False
    static: bool = False
    value: Any = None
    literal: str = None
    access: str = "public"  # for class member


@dataclass(repr=False)
class Function(Symbol):
    ret_type: str = ""
    parent: Optional["Namespace"] = None
    args: List[Variable] = field(default_factory=list)
    calling_convention: str = "__cdecl"

    # impl
    body: Optional[list[any]] = field(default_factory=list)

    @property
    def address(self):
        """function itself doesn't know whether it is overloaded."""
        return f"&{self.full_name}"

    @property
    def type(self, show_calling_convention: bool = False):
        args = ",".join([i.type for i in self.args])
        calling = (
            self.calling_convention + " " if show_calling_convention else ""
        )
        return f"{self.ret_type}({calling} *)({args})"

    @property
    def args_signature(self):
        return ",".join(f"{arg.type} {arg.name}" for arg in self.args)

    @property
    def signature(self):
        s = f"{self.full_name} ({self.args_signature})"
        return s

    def __str__(self):
        return self.signature

    def __hash__(self):
        return hash(self.signature)


@dataclass(repr=False, unsafe_hash=True)
class Method(Function):
    ret_type: str = ""
    parent: "Class" = None
    access: str = "public"
    is_virtual: bool = False
    is_pure_virtual: bool = False
    is_static: bool = False
    is_final: bool = False

    @property
    def type(self, show_calling_convention: bool = False):
        args = ",".join([i.type for i in self.args])
        calling = (
            self.calling_convention + " " if show_calling_convention else ""
        )
        parent_prefix = ""
        if not self.is_static:
            parent_prefix = f"{self.parent.full_name}::"
        return f"{self.ret_type}({calling}{parent_prefix}*)({args})"

    def declaration_in_class(self):
        return "{access}: {virtual}{static}{ret} {name}({args}){pure_virtual}".format(
            access=f"{self.access}",
            virtual="virtual " if self.is_virtual else "",
            static="static " if self.is_static else "",
            ret=self.ret_type,
            name=self.name,
            args=self.args_signature,
            pure_virtual=" = 0" if self.is_pure_virtual else "",
        )

    def declaration_global(self):
        return "{ret} {scope}{name}({args}){pure_virtual}".format(
            ret=self.ret_type,
            name=self.name,
            scope=f"{self.parent.full_name}::" if self.parent else "",
            args=self.args_signature,
            pure_virtual=" = 0" if self.is_pure_virtual else "",
        )

    @property
    def signature(self):
        return "{access} {virtual}{static} {scope}{signature}{pure_virtual}".format(
            access=self.access,
            virtual="virtual" if self.is_virtual else "",
            static="static" if self.is_static else "",
            scope=f"{self.parent.name}::" if self.parent else "",
            signature=super().signature,
            pure_virtual=" = 0" if self.is_pure_virtual else "",
        )

    def __str__(self):
        return self.signature


@dataclass(repr=False)
class Namespace(Symbol):
    parent: Optional["Namespace"] = None
    enums: Dict[str, "Enum"] = field(default_factory=dict)
    typedefs: Dict[str, Typedef] = field(default_factory=dict)
    classes: Dict[str, "Class"] = field(default_factory=dict)
    template_classes: Dict[str, "TemplateClass"] = field(default_factory=dict)
    variables: Dict[str, Variable] = field(default_factory=dict)
    functions: Dict[str, List[Function]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    namespaces: Dict[str, "Namespace"] = field(default_factory=dict)

    # implementations
    forward_declares: list[str] = field(default_factory=list)
    using_namespaces: list[str] = field(default_factory=list)
    method_impls: list[Method] = field(default_factory=list)
    function_impls: list[Function] = field(default_factory=list)

    def extend(self, other: "Namespace"):
        self.enums.update(other.enums)
        self.typedefs.update(other.typedefs)
        self.classes.update(other.classes)
        self.variables.update(other.variables)
        self.functions.update(other.functions)
        for name, n in other.namespaces.items():
            if name in self.namespaces:
                self.namespaces[name].extend(n)
            else:
                self.namespaces[name] = n
        pass


@dataclass(repr=False)
class Enum(Symbol):
    type: str = ""
    parent: Optional["AnyCxxSymbol"] = None
    variables: Dict[str, Variable] = field(default_factory=dict)
    is_strong_typed: bool = False


@dataclass(repr=False)
class Class(Namespace):
    parent: Optional["AnyCxxSymbol"] = None
    super: List["Class"] = field(default_factory=list)
    functions: Dict[str, List["Method"]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    constructors: List["Method"] = field(default_factory=list)
    destructor: "Method" = None

    is_polymorphic: bool = False  # has virtual methods

    can_generate_wrapper: bool = (
        True  # generate a wrapper if it is a polymorphic class
    )

    def __str__(self):
        return "class " + self.name


@dataclass(repr=False)
class File(Namespace):
    directory: str = ""
    relative_includes: list[str] = field(default_factory=list)
    absolute_includes: list[str] = field(default_factory=list)
    pragma_once: bool = False

    @property
    def filename(self) -> str:
        return self.name

    @property
    def full_name(self):
        return ""

    @property
    def filepath(self) -> str:
        return f"{self.directory}/{self.name}"


@dataclass(repr=False)
class AnonymousUnion(Class):
    scope_name: str = ""  # same as its variable_name in parent

    @property
    def full_name(self):
        if self.scope_name:
            return f"decltype({self.parent.full_name}::{self.scope_name})"
        else:
            return self.parent.full_name


@dataclass(repr=False)
class TemplateClass(Class):
    pass


AnyCxxSymbol = Union[
    Symbol,
    Macro,
    Typedef,
    Variable,
    Function,
    Method,
    Namespace,
    Enum,
    Class,
]
