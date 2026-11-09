"""Map legacy plugin imports onto the canonical modules, without duplicate Qt types."""
import importlib
import importlib.abc
import importlib.util
import sys


class _LegacyLoader(importlib.abc.Loader):
    def __init__(self, canonical):
        self.canonical = canonical

    def create_module(self, spec):
        module = importlib.import_module(self.canonical)
        self.original_spec = module.__spec__
        return module

    def exec_module(self, module):
        module.__spec__ = self.original_spec


class _LegacyFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith('ISAT.'):
            return None
        canonical = 'yolo_backprop' + fullname[len('ISAT'):]
        spec = importlib.util.find_spec(canonical)
        if spec is None:
            return None
        return importlib.util.spec_from_loader(
            fullname, _LegacyLoader(canonical), is_package=spec.submodule_search_locations is not None)


def install_legacy_imports():
    sys.modules.setdefault('ISAT', sys.modules['yolo_backprop'])
    if not any(isinstance(finder, _LegacyFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _LegacyFinder())
