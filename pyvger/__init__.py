"""pyvger - interact with Ex Libris Voyager"""
import os

from pyvger.core import Voy
from pyvger.helper import recode

os.environ["NLS_LANG"] = "American_America.UTF8"

__version__ = "0.8.0"

__all__ = [Voy]
