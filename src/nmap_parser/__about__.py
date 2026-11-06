"""Single source of truth for package metadata.

``pyproject.toml`` reads ``__version__`` from this module via
``[tool.setuptools.dynamic]``, so the version is never duplicated.
"""

__version__ = "2.0.1"
__author__ = "test233"
__license__ = "MIT"
