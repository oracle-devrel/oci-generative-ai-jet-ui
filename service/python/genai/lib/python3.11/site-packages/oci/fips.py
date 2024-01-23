# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import absolute_import
import sys
import ctypes
import logging
import os


class DevNull:
    """
    Simple class to supress errors which may occur when importing hashlib
    in FIPS mode.
    """
    def write(self, msg):
        pass


def override_libcrypto(fips_libcrypto_path):
    """
    Override libcrypto and add FIPS_mode function to ssl if it is not there
    """

    _bs_crypto = ctypes.CDLL(fips_libcrypto_path)
    _bs_crypto.FIPS_mode_set(ctypes.c_int(1))
    import ssl  # noqa: E402
    if not hasattr(ssl, 'FIPS_mode'):
        ssl.FIPS_mode = _bs_crypto.FIPS_mode


def md5(intitial_message=''):
    """
    Placeholder md5 function for hashlib so it won't segfault when called after
    enabling FIPS mode.
    """
    raise ValueError("md5 disabled for fips")
    return None


def patch_hashlib_md5():
    """
    hashlib.md5 is imported by urllib3, which is required by requests,
    which is used by oci (python sdk).  This will cause errors so we need to
    patch hashlib.
    """

    stderr = sys.stderr
    try:
        sys.stderr = DevNull()
        import hashlib  # noqa: E402
    except (RuntimeError, ValueError):
        pass
    sys.stderr = stderr
    hashlib.md5 = md5


def is_fips_mode():
    """
    Verify that ssl.FIPS_mode() returns 1 and that using md5 raises an
    exception
    """

    import hashlib
    import ssl

    if not hasattr(ssl, 'FIPS_mode'):
        return False
    elif ssl.FIPS_mode() != 1:
        return False

    try:
        digest = hashlib.md5(b"Hello World\n").hexdigest()  # noqa: F841
        return False
    except ValueError:
        # Expect to get this exception so do nothing
        pass

    return True


def enable_fips_mode(fips_libcrypto_path=None):
    """
    Enable FIPS mode by overriding libcrypto and patching hashlib
    """

    logger = logging.getLogger("{}.{}".format(__name__, id(enable_fips_mode)))
    logger.addHandler(logging.NullHandler())

    if not fips_libcrypto_path:
        if 'FIPS_LIBCRYPTO_PATH' in os.environ:
            fips_libcrypto_path = os.environ['FIPS_LIBCRYPTO_PATH']
        elif 'OCI_PYTHON_SDK_FIPS_LIBCRYPTO_PATH' in os.environ:
            fips_libcrypto_path = os.environ['OCI_PYTHON_SDK_FIPS_LIBCRYPTO_PATH']

    if fips_libcrypto_path:
        override_libcrypto(fips_libcrypto_path)

        import hashlib
        try:
            digest = hashlib.md5(b"Hello World\n").hexdigest()  # noqa: F841

            # If the previous line did not raise an exception md5 needs to be
            # patched
            patch_hashlib_md5()

        except ValueError:
            # Expect to get this exception so do nothing
            pass

        logger.info("Using '{}' for libcypto".format(fips_libcrypto_path))
        if is_fips_mode():
            logger.info("FIPS mode is active")
        else:
            logger.error("Failed to enter FIPS mode")
