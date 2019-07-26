import ast
import re

from setuptools import find_packages, setup

with open("c2py/__init__.py", "rb") as f:
    version_line = re.search(
        r"__version__\s+=\s+(.*)", f.read().decode("utf-8")
    ).group(1)
    version = str(ast.literal_eval(version_line))

install_requires = [
    "click",
]

setup(
    name="c2py",
    version=version,
    packages=find_packages(exclude=["tests.", ]),
    install_requires=install_requires,
        entry_points={
        'console_scripts': [
            'c2py=c2py.cli:cli',
        ]
    },
    package_data={"": [
        "*.h",
        "*.hpp",
        "*.cpp",
        "*.c",
        "*.py.in",
        "*.dll",
    ]},
)
