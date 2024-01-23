# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes


class md5:
    """
    Wrapper for MD5 implementation in cryptography for when the hashlib MD5
    implementation has be turned off due to FIPS
    """

    def __init__(self):
        self._digest = hashes.Hash(hashes.MD5(), backend=default_backend())

    def update(self, message):
        data = message
        if isinstance(message, memoryview):
            data = message.tobytes()

        self._digest.update(data)

    def digest(self):
        return self._digest.finalize()
