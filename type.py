#encoding: utf-8

base_types = ['char8_t', 'char16_t', 'char32_t', 'wchar_t',
              'char', 'short', 'int', 'long',
              'long long'
              'unsigned char', 'unsigned short', 'unsigned int',
              'unsigned long', 'unsigned long long',
              'float', 'double',
              ]


def _is_array_type(t: str):
    return '[' in t


def _array_base(t: str):
    """
    :raise ValueError if t is not a array type
    """
    return t[:t.index('[') - 1]


def _is_pointer_type(t: str):
    return "*" in t


def _is_reference_type(t: str):
    return "&" in t


def remove_cvref(t: str):
    return t.replace("const ", "").replace("*", "").replace("&", "").replace(" ", "")
