try:
    from ._version import __version__
except ImportError:
    # Fallback for development installs
    __version__ = "dev"

from .logger import logger

__all__ = ["__version__", "logger"]
