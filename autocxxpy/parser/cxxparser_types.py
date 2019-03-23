from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Variable:
    name: str
    type: str
    parent: Any = None
    constant: bool = False
    static: bool = False
    default: Any = None


@dataclass
class LiteralVariable(Variable):
    literal: str = None
    literal_valid: bool = True


@dataclass
class Enum:
    name: str
    type: str
    parent: "Namespace" = None
    values: Dict[str, Variable] = field(default_factory=dict)
    is_strong_typed: bool = False

    @property
    def full_name(self):
        if self.parent is None:
            # return "::" + self.name
            return self.name
        return self.parent.full_name + "::" + self.name

    def full_name_of(self, v: Variable):
        return self.full_name + "::" + v.name


@dataclass
class Function:
    name: str
    ret_type: str
    parent: "Namespace" = None
    args: List[Variable] = field(default_factory=list)
    calling_convention: str = "__cdecl"

    @property
    def type(self, show_calling_convention: bool = False):
        args = ",".join([i.type for i in self.args])
        calling = (
            self.calling_convention + " " if show_calling_convention else ""
        )
        return f"{self.ret_type}({calling} *)({args})"

    @property
    def full_name(self):
        return f"::{self.name}"

    @property
    def signature(self):
        s = f"{self.name} ("
        for arg in self.args:
            s += arg.type + " " + arg.name + ","
        s = s[:-2] + ")"
        return s

    def __str__(self):
        return self.signature


@dataclass
class Namespace:
    name: str = ""
    parent: "Namespace" = None
    enums: Dict[str, Enum] = field(default_factory=dict)
    typedefs: Dict[str, str] = field(default_factory=dict)
    classes: Dict[str, "Class"] = field(default_factory=dict)
    variables: Dict[str, Variable] = field(default_factory=dict)
    functions: Dict[str, List[Function]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    namespaces: Dict[str, "Namespace"] = field(default_factory=dict)

    @property
    def full_name(self):
        if self.parent is None:
            return self.name
        return self.parent.full_name + "::" + self.name


@dataclass
class Class(Namespace):
    name: str = ""
    functions: Dict[str, List["Method"]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    constructors: List["Method"] = field(default_factory=list)
    destructor: "Method" = None

    is_polymorphic: bool = False

    def __str__(self):
        return "class " + self.name

    # without this, PyCharm will crash
    def __repr__(self):
        return "class" + self.name


@dataclass
class Method(Function):
    name: str = ''
    ret_type: str = ''
    parent: Class = None
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

    @property
    def full_name(self):
        return f"{self.parent.name}::{self.name}"

    @property
    def signature(self):
        return (
            "{} {}{} {}::".format(
                self.access,
                "virtual" if self.is_virtual else "",
                "static" if self.is_static else "",
                self.parent.name,
            ) +
            super().signature +
            (" = 0" if self.is_pure_virtual else "")
        )

    def __str__(self):
        return self.signature
