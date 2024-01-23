"""
Type wrangling utility functions.
"""

from .constants import *
from .mechanisms import *


cdef CK_BYTE_buffer(length):
    """Make a buffer for `length` CK_BYTEs."""
    return array(shape=(length,), itemsize=sizeof(CK_BYTE), format='B')


cdef CK_ULONG_buffer(length):
    """Make a buffer for `length` CK_ULONGs."""
    return array(shape=(length,), itemsize=sizeof(CK_ULONG), format='L')


cdef bytes _pack_attribute(key, value):
    """Pack a Attribute value into a bytes array."""

    try:
        pack, _ = ATTRIBUTE_TYPES[key]
        return pack(value)
    except KeyError:
        raise NotImplementedError("Can't pack this %s. "
                                  "Expand ATTRIBUTE_TYPES!" % key)


cdef _unpack_attributes(key, value):
    """Unpack a Attribute bytes array into a Python value."""

    try:
        _, unpack = ATTRIBUTE_TYPES[key]
        return unpack(bytes(value))
    except KeyError:
        raise NotImplementedError("Can't unpack this %s. "
                                  "Expand ATTRIBUTE_TYPES!" % key)
