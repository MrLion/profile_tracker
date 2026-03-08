"""
Strategy auto-discovery.
Finds all Strategy subclasses in this package and registers them by slug.
"""

import importlib
import pkgutil
from strategies.base import Strategy


def discover_strategies() -> dict[str, Strategy]:
    strategies = {}
    package_path = __path__
    for importer, modname, ispkg in pkgutil.iter_modules(package_path):
        if modname == "base":
            continue
        module = importlib.import_module(f".{modname}", __package__)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, Strategy)
                    and attr is not Strategy):
                instance = attr()
                strategies[instance.slug] = instance
    return strategies
