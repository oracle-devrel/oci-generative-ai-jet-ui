"""
:mod:`pkcs11` defines a high-level, "Pythonic" interface to PKCS#11.
"""

from .constants import *  # noqa: F403
from .exceptions import *  # noqa: F403
from .mechanisms import *  # noqa: F403
from .types import *  # noqa: F403


_so = None
_lib = None


def lib(so):
    """
    Wrap the main library call coming from Cython with a preemptive
    dynamic loading.
    """
    global _lib
    global _so

    if _lib:
        if _so != so:
            raise AlreadyInitialized(  # noqa: F405
                "Already initialized with %s" % so)
        else:
            return _lib

    from . import _pkcs11

    _lib = _pkcs11.lib(so)
    _so = so

    return _lib
