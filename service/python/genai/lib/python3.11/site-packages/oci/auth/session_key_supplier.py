# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

import threading


class SessionKeySupplier(object):
    # Magic number recommended by cryptography.io docs. Also see: http://www.daemonology.net/blog/2009-06-11-cryptographic-right-answers.html
    PUBLIC_EXPONENT = 65537

    def __init__(self, key_size=2048):
        """
        A supplier which vends public and private keys, and can refresh the keys it uses.

        :param int key_size (optional):
            The key size to use when generating private keys. Defaults to 2048 if not provided.
        """
        self.key_size = key_size
        self.private_key = rsa.generate_private_key(
            public_exponent=self.PUBLIC_EXPONENT,
            key_size=self.key_size,
            backend=default_backend()
        )

        self._refresh_lock = threading.Lock()

    def get_key_pair(self):
        self._refresh_lock.acquire()
        private_key = self.private_key
        self._refresh_lock.release()

        return {'private': private_key, 'public': private_key.public_key()}

    def refresh(self):
        self._refresh_lock.acquire()
        try:
            self.private_key = rsa.generate_private_key(
                public_exponent=self.PUBLIC_EXPONENT,
                key_size=self.key_size,
                backend=default_backend()
            )
        finally:
            self._refresh_lock.release()
