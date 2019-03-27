from autocxxpy.types.generator_types import GeneratorSymbol, GeneratorTypedef


class ObjectManager(dict):

    def __getitem__(self, item: str) -> "GeneratorSymbol":
        if not item.startswith('::'):
            item = "::" + item
        return super().__getitem__(item)

    def resolve_all_typedef(self, t: str):
        c = self.__getitem__(t)
        if isinstance(c, GeneratorTypedef):
            return self.resolve_all_typedef(c.target)
        return c
