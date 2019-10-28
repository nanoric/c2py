# encoding: utf-8
import functools
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum as enum
from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Union

from c2py.core.core_types.parser_types import (AnyCxxSymbol, Class, Enum, Function, Macro,
                                               Method,
                                               Namespace, Symbol, TemplateClass, Typedef,
                                               Variable, AnonymousUnion)

if TYPE_CHECKING:
    from c2py.objects_manager import ObjectManager
    from c2py.core.wrappers import WrapperInfo


class CallingType(enum):
    Default = 0
    Async = 1
    Sync = 2


SymbolFilterType = Callable[[Symbol], bool]


def default_symbol_filter(_: Symbol):
    return True


@dataclass()
class GeneratorSymbol(Symbol):
    generate: bool = True  # change this to False to disable generating of this symbol
    alias: str = ""

    def __repr__(self):
        return f"{self.__class__.__name__} {self.full_name}"

    def post_init(self, objects: "ObjectManager" = None, symbol_filter: SymbolFilterType = None):
        if not self.alias:
            self.alias = self.name


@dataclass(repr=False)
class GeneratorMacro(Macro, GeneratorSymbol):
    definition: str = ""


@dataclass(repr=False)
class GeneratorTypedef(Typedef, GeneratorSymbol):
    target: str = ""


@dataclass(repr=False)
class GeneratorVariable(Variable, GeneratorSymbol):
    alias: str = ""

    def post_init(self, objects: "ObjectManager" = None, symbol_filter: SymbolFilterType = None):
        if not self.alias:
            self.alias = self.name


@dataclass(repr=False)
class GeneratorVariableFromMacro(GeneratorVariable):
    pass


@dataclass(repr=False)
class GeneratorFunction(Function, GeneratorSymbol):
    ret_type: str = ''

    wrappers: List["WrapperInfo"] = field(default_factory=list)

    calling_type: CallingType = CallingType.Default
    args: List[GeneratorVariable] = field(default_factory=list)
    has_overload: bool = False

    @property
    def address(self):
        if self.has_overload:
            return f'static_cast<{self.type}>(&{self.full_name})'
        return f'&{self.full_name}'

    def post_init(self, objects: "ObjectManager" = None, symbol_filter: SymbolFilterType = None):
        super().post_init(objects)
        self.args = to_generator_type(
            self.args,
            self, objects=objects,
            symbol_filter=default_symbol_filter,  # don't filter arguments
        )
        self.wrappers = list(self.wrappers)  # make a copy

    def _resolve_wrapper(self, wi: "WrapperInfo"):
        return wi.wrapper.wrap(f=copy(self), index=wi.index, wrapper_info=wi)

    def resolve_wrappers(self):
        f: "GeneratorFunction" = copy(self)
        for wi in self.wrappers:
            f = f._resolve_wrapper(wi)
        return f


@dataclass(repr=False)
class GeneratorMethod(Method, GeneratorFunction, GeneratorSymbol):
    ret_type: str = ''
    alias: str = ""
    parent: Class = None


@dataclass(repr=False)
class GeneratorNamespace(Namespace, GeneratorSymbol):
    parent: "GeneratorNamespace" = None
    alias: str = ""

    enums: Dict[str, "GeneratorEnum"] = field(default_factory=dict)
    typedefs: Dict[str, "GeneratorTypedef"] = field(default_factory=dict)
    classes: Dict[str, "GeneratorClass"] = field(default_factory=dict)
    template_classes: Dict[str, "GeneratorTemplateClass"] = field(default_factory=dict)
    variables: Dict[str, "GeneratorVariable"] = field(default_factory=dict)
    functions: Dict[str, List["GeneratorFunction"]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    namespaces: Dict[str, "GeneratorNamespace"] = field(default_factory=dict)

    def post_init(self, objects: "ObjectManager" = None, symbol_filter: SymbolFilterType = None):
        super().post_init(objects=objects, symbol_filter=symbol_filter)
        self.classes = to_generator_type(self.classes, self, objects=objects,
                                         symbol_filter=symbol_filter)
        self.enums = to_generator_type(self.enums, self, objects=objects,
                                       symbol_filter=symbol_filter)
        self.variables = to_generator_type(self.variables, self, objects=objects,
                                           symbol_filter=symbol_filter)
        self.functions = to_generator_type(self.functions, self, objects=objects,
                                           symbol_filter=symbol_filter)
        self.namespaces = to_generator_type(self.namespaces, self, objects=objects,
                                            symbol_filter=symbol_filter)
        self.typedefs = to_generator_type(self.typedefs, self, objects=objects,
                                          symbol_filter=symbol_filter)


@dataclass(repr=False)
class GeneratorEnum(Enum, GeneratorSymbol):
    type: str = ''
    alias: str = ""

    variables: Dict[str, GeneratorVariable] = field(default_factory=dict)

    def post_init(self, objects: "ObjectManager" = None, symbol_filter: SymbolFilterType = None):
        super().post_init()
        self.variables = to_generator_type(self.variables, self, objects=objects,
                                           symbol_filter=symbol_filter)


@dataclass(repr=False)
class GeneratorClass(Class, GeneratorNamespace, GeneratorSymbol):
    super: List["GeneratorClass"] = field(default_factory=list)
    functions: Dict[str, List[GeneratorMethod]] = field(
        default_factory=(lambda: defaultdict(list))
    )
    force_to_dict: bool = False  # if need_wrap is true, wrap this to dict(deprecated)
    # generator will not assign python constructor for pure virtual
    is_pure_virtual: bool = False
    generate_caster: bool = True

    def post_init(self, objects: "ObjectManager" = None, symbol_filter: SymbolFilterType = None):
        super().post_init(objects=objects, symbol_filter=symbol_filter)
        self.super = to_generator_type(self.super, None, objects=None,
                                       symbol_filter=symbol_filter)
        pass


@dataclass(repr=False)
class GeneratorAnonymousUnion(AnonymousUnion, GeneratorClass):
    pass


@dataclass(repr=False)
class GeneratorTemplateClass(GeneratorClass, GeneratorSymbol):
    pass


def to_generator_dict(c: Dict[str, AnyCxxSymbol],
                      parent: "AnyGeneratorSymbol",
                      objects: Optional["ObjectManager"],
                      symbol_filter: SymbolFilterType = default_symbol_filter):
    assert isinstance(c, dict)
    return {
        k: to_generator_type(v, parent, objects=objects, symbol_filter=symbol_filter)
        for k, v in c.items()
        if (symbol_filter(v) if isinstance(v, Symbol) else True)
    }


def to_generator_list(l: List[AnyCxxSymbol],
                      parent,
                      objects,
                      symbol_filter: SymbolFilterType = default_symbol_filter):
    assert isinstance(l, list)
    return [
        to_generator_type(i, parent, objects=objects, symbol_filter=symbol_filter)
        for i in l
        if (symbol_filter(i) if isinstance(i, Symbol) else True)
    ]


def dataclass_convert(func):
    @functools.wraps(func)
    def wrapper(v, parent, objects: "ObjectManager", symbol_filter: SymbolFilterType):
        kwargs = v.__dict__
        if parent:
            kwargs['parent'] = parent
        v = func(**kwargs)
        v.post_init(objects=objects, symbol_filter=symbol_filter)
        if objects is not None:
            objects[v.full_name] = v
        return v

    return wrapper


def to_generator_type(v: Union["AnySymbol", Dict, List, defaultdict],
                      parent, objects, symbol_filter: SymbolFilterType = default_symbol_filter):
    if v is None:
        return None
    t = type(v)
    assert t in mapper
    wrapper = mapper[t]
    v = wrapper(v, parent, objects, symbol_filter)
    return v


def filter_symbols(v: Union["AnySymbol", Dict, List, defaultdict],
                   symbol_filter: SymbolFilterType = default_symbol_filter):
    return to_generator_type(v=v, parent=v.parent, objects=None, symbol_filter=symbol_filter)


def copy(v: "AnyGeneratorSymbol"):
    nv = to_generator_type(v, v.parent, None)
    return nv


mapper = {
    defaultdict: to_generator_dict,
    dict: to_generator_dict,
    list: to_generator_list,

    Macro: dataclass_convert(GeneratorMacro),
    Typedef: dataclass_convert(GeneratorTypedef),
    Variable: dataclass_convert(GeneratorVariable),
    Function: dataclass_convert(GeneratorFunction),
    Method: dataclass_convert(GeneratorMethod),
    Namespace: dataclass_convert(GeneratorNamespace),
    Enum: dataclass_convert(GeneratorEnum),
    Class: dataclass_convert(GeneratorClass),
    AnonymousUnion: dataclass_convert(GeneratorAnonymousUnion),
    TemplateClass: dataclass_convert(GeneratorClass),

    GeneratorMacro: dataclass_convert(GeneratorMacro),
    GeneratorTypedef: dataclass_convert(GeneratorTypedef),
    GeneratorVariable: dataclass_convert(GeneratorVariable),
    GeneratorVariableFromMacro: dataclass_convert(GeneratorVariableFromMacro),
    GeneratorFunction: dataclass_convert(GeneratorFunction),
    GeneratorMethod: dataclass_convert(GeneratorMethod),
    GeneratorNamespace: dataclass_convert(GeneratorNamespace),
    GeneratorEnum: dataclass_convert(GeneratorEnum),
    GeneratorClass: dataclass_convert(GeneratorClass),
    GeneratorAnonymousUnion: dataclass_convert(GeneratorAnonymousUnion),

    GeneratorTemplateClass: dataclass_convert(GeneratorClass),
}

AnyGeneratorSymbol = Union[
    GeneratorSymbol,
    GeneratorTypedef,
    GeneratorMacro,
    GeneratorVariable,
    GeneratorVariableFromMacro,
    GeneratorFunction,
    GeneratorMethod,
    GeneratorNamespace,
    GeneratorEnum,
    GeneratorClass,
    GeneratorAnonymousUnion,
    GeneratorTemplateClass,
]

AnySymbol = Union[AnyGeneratorSymbol, AnyCxxSymbol]
