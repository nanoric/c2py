from autocxxpy.types.generator_types import GeneratorSymbol, GeneratorTypedef


class ObjectManager(dict):

    def __setitem__(self, key: str, value: "GeneratorSymbol"):
        if self.__contains__(key):
            v = self.__getitem__(key)
            if v is None:
                return super().__setitem__(key, value)
            if not isinstance(v, GeneratorTypedef) and isinstance(value, GeneratorTypedef):
                # handle special case: typedef enum/struct Name{} Name;
                return  # don't use a typedef to override original type
        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> "GeneratorSymbol":
        if not key.startswith('::'):
            key = "::" + key
        return super().__getitem__(key)

    def __contains__(self, key: str):
        if not key.startswith('::'):
            key = "::" + key
        return super().__contains__(key)

    def resolve_all_typedef(self, t: str):
        c = self.__getitem__(t)
        if isinstance(c, GeneratorTypedef) and t != c.target:
            return self.resolve_all_typedef(c.target)
        return c
