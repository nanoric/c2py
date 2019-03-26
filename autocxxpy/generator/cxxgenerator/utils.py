import re


def slugify(value):
    value = re.sub(r'[^\w\s-]', '_', value).strip()
    return re.sub(r'[_\s]+', '_', value)