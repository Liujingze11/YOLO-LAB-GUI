"""Writable app data paths, usable in algorithm workers without importing Qt."""
import os
import sys
from pathlib import Path


def data_dir() -> Path:
    explicit = os.environ.get('ISAT_MODEL_DATA_DIR')
    if explicit:
        return Path(explicit).expanduser().resolve()
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', str(Path.home()/'AppData'/'Roaming')))
    elif sys.platform == 'darwin':
        base = Path.home()/'Library'/'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local'/'share')))
    return base/'ISAT'/'model-development'
