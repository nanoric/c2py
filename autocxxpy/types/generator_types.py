# encoding: utf-8
import functools
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

from autocxxpy.types.parser_types import (AnyCxxSymbol, Class, Enum, Function, Method, Namespace,
                                          TemplateClass, Typedef, Variable, Symbol)


@dataclass(repr=False)
class GeneratorVariable(Variable):
    alias: str = ""

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name


@dataclass(repr=False)
class GeneratorNamespace(Namespace):
    parent: "GeneratorNamespace" = None
    alias: str = ""

    enums: Dict[str, "GeneratorEnum"] = field(default_factory=dict)
    typedefs: Dict[str, Typedef] = field(default_factory=dict)
    classes: Dict[str, "GeneratorClass"] = field(default_factory=dict)
    template_classes: Dict[str, "GeneratorTemplateClass"] = field(default_factory=dict)
    variables: Dict[str, "GeneratorVariable"] = field(default_factory=dict)
    functions: Dict[str, List["GeneratorFunction"]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    namespaces: Dict[str, "GeneratorNamespace"] = field(default_factory=dict)
    objects: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name
        self.classes = to_generator_type(self.classes, self, objects=self.objects)
        self.enums = to_generator_type(self.enums, self, objects=self.objects)
        self.variables = to_generator_type(self.variables, self, objects=self.objects)
        self.functions = to_generator_type(self.functions, self, objects=self.objects)
        self.namespaces = to_generator_type(self.namespaces, self, objects=self.objects)
        self.typedefs = to_generator_type(self.typedefs, self, objects=self.objects)


class CallingType(Enum):
    Default = 0
    Async = 1
    Sync = 2


@dataclass(repr=False)
class GeneratorFunction(Function, GeneratorNamespace):
    ret_type: str = ''
    alias: str = ""

    calling_type = CallingType.Default
    args: List[GeneratorVariable] = field(default_factory=list)

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name
        self.args = to_generator_type(self.args, self, objects=self.objects)


@dataclass(repr=False)
class GeneratorEnum(GeneratorNamespace, Enum):
    type: str = ''
    alias: str = ""

    values: Dict[str, GeneratorVariable] = field(default_factory=dict)

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name
        self.values = to_generator_type(self.values, self, objects=self.objects)


@dataclass(repr=False)
class GeneratorMethod(Method, GeneratorFunction, GeneratorNamespace):
    ret_type: str = ''
    alias: str = ""
    parent: Class = None
    has_overload: bool = False


@dataclass(repr=False)
class GeneratorClass(Class, GeneratorNamespace):
    super: List["GeneratorClass"] = field(default_factory=list)
    functions: Dict[str, List[GeneratorMethod]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    force_to_dict: bool = False  # if need_wrap is true, wrap this to dict(deprecated)
    # generator will not assign python constructor for pure virtual
    is_pure_virtual: bool = False


@dataclass(repr=False)
class GeneratorTemplateClass(GeneratorClass):
    pass


def to_generator_dict(c: Dict[str, AnyCxxSymbol], parent, objects):
    assert isinstance(c, dict)
    return {k: to_generator_type(v, parent, objects=objects) for k, v in c.items()}


def to_generator_list(l: List[AnyCxxSymbol], parent, objects):
    assert isinstance(l, list)
    return [to_generator_type(i, parent, objects=objects) for i in l]


def dataclass_convert(func):
    @functools.wraps(func)
    def wrapper(v, parent, objects):
        kwargs = v.__dict__
        if parent:
            kwargs['parent'] = parent
        v = func(
            **kwargs
        )
        objects[v.full_name] = v
        if hasattr(v, "objects"):
            v.objects = objects
        return v

    return wrapper


def to_generator_type(v: Union["AnySymbol", Dict, List, defaultdict],
                      parent, objects):
    if v is None:
        return None
    t = type(v)
    assert t in mapper
    wrapper = mapper[t]
    v = wrapper(v, parent, objects)
    return v


mapper = {
    defaultdict: to_generator_dict,
    dict: to_generator_dict,
    list: to_generator_list,

    Typedef: dataclass_convert(Typedef),
    Variable: dataclass_convert(GeneratorVariable),
    Enum: dataclass_convert(GeneratorEnum),
    Class: dataclass_convert(GeneratorClass),
    TemplateClass: dataclass_convert(GeneratorClass),
    Namespace: dataclass_convert(GeneratorNamespace),
    Method: dataclass_convert(GeneratorMethod),
    Function: dataclass_convert(GeneratorFunction),

    GeneratorVariable: dataclass_convert(GeneratorVariable),
    GeneratorEnum: dataclass_convert(GeneratorEnum),
    GeneratorClass: dataclass_convert(GeneratorClass),
    GeneratorTemplateClass: dataclass_convert(GeneratorClass),
    GeneratorNamespace: dataclass_convert(GeneratorNamespace),
    GeneratorMethod: dataclass_convert(GeneratorMethod),
    GeneratorFunction: dataclass_convert(GeneratorFunction),
}

AnyGeneratorSymbol = Union[
    Symbol,
    Typedef,
    GeneratorVariable,
    GeneratorEnum,
    GeneratorClass,
    GeneratorTemplateClass,
    GeneratorNamespace,
    GeneratorMethod,
    GeneratorFunction,
]

AnySymbol = Union[AnyGeneratorSymbol, AnyCxxSymbol]
