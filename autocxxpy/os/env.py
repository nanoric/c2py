import os

DEFAULT_INCLUDE_PATHS = []

if 'INCLUDE' in os.environ:
    DEFAULT_INCLUDE_PATHS.extend(os.environ['INCLUDE'].split(os.path.pathsep))
