"""pyvger - interact with Ex Libris Voyager."""
import os

from pyvger.core import Voy
from pyvger.helper import recode
from pyvger.version import __version__

os.environ["NLS_LANG"] = "American_America.UTF8"


__all__ = ["Voy", "__version__", "recode"]
