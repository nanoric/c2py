from autocxxpy.types.generator_types import GeneratorSymbol, GeneratorTypedef


class ObjectManager(dict):

    def __setitem__(self, key: str, value: "GeneratorSymbol"):
        if self.__contains__(key):
            if isinstance(value, GeneratorTypedef):
                # handle special case: typedef enum/struct Name{} Name;
                return  # don't use a typedef to override original type
        super().__setitem__(key, value)

    def __getitem__(self, item: str) -> "GeneratorSymbol":
        if not item.startswith('::'):
            item = "::" + item
        return super().__getitem__(item)

    def resolve_all_typedef(self, t: str):
        c = self.__getitem__(t)
        if isinstance(c, GeneratorTypedef) and t != c.target:
            return self.resolve_all_typedef(c.target)
        return c
