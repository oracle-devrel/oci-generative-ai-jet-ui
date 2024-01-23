# coding: utf-8
# Modified Work: Copyright (c) 2018, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.
# Original Work: Copyright (c) 2014 Adam Knight
# Original Work: Copyright (c) 2012 Adam T. Lindsay (original author)

import base64
from oci._vendor import six

from cryptography.hazmat.backends import default_backend  # noqa: F401
from cryptography.hazmat.primitives import hashes, hmac, serialization  # noqa: F401
from cryptography.hazmat.primitives.asymmetric import rsa, padding  # noqa: F401

from .utils import *  # noqa: F403


DEFAULT_SIGN_ALGORITHM = "hmac-sha256"


class Signer(object):
    """
    When using an RSA algo, the secret is a PEM-encoded private or public key.
    When using an HMAC algo, the secret is the HMAC signing secret.

    Password-protected keyfiles are not supported.
    """
    def __init__(self, secret, algorithm=None):
        if algorithm is None:
            algorithm = DEFAULT_SIGN_ALGORITHM

        assert algorithm in ALGORITHMS, "Unknown algorithm"  # noqa: F405
        if isinstance(secret, six.string_types):
            secret = secret.encode("ascii")

        self._rsa_public = None
        self._rsa_private = None
        self._hash = None
        self.sign_algorithm, self.hash_algorithm = algorithm.split('-')

        if self.sign_algorithm == 'rsa':
            try:
                self._rsahash = HASHES[self.hash_algorithm]  # noqa: 405
                self._rsa_private = serialization.load_pem_private_key(
                    secret,
                    None,
                    backend=default_backend()
                )
                self._rsa_public = self._rsa_private.public_key()
            except ValueError as e:  # noqa: F841
                try:
                    self._rsa_public = serialization.load_pem_public_key(
                        secret,
                        backend=default_backend()
                    )
                except ValueError as e:  # noqa: F841
                    raise HttpSigException("Invalid key.")  # noqa: 405
        elif self.sign_algorithm == 'hmac':
            self._hash = hmac.HMAC(
                secret,
                HASHES[self.hash_algorithm](),  # noqa: 405
                backend=default_backend()
            )

    @property
    def algorithm(self):
        return '%s-%s' % (self.sign_algorithm, self.hash_algorithm)

    def _sign_rsa(self, data):
        if isinstance(data, six.string_types):
            data = data.encode("ascii")
        return self._rsa_private.sign(data, padding.PKCS1v15(), self._rsahash())

    def _sign_hmac(self, data):
        if isinstance(data, six.string_types):
            data = data.encode("ascii")
        hmac = self._hash.copy()
        hmac.update(data)
        return hmac.finalize()

    def _sign(self, data):
        if isinstance(data, six.string_types):
            data = data.encode("ascii")

        signed = None
        if self._rsa_private:
            signed = self._sign_rsa(data)
        elif self._hash:
            signed = self._sign_hmac(data)
        if not signed:
            raise SystemError('No valid encryptor found.')
        return base64.b64encode(signed).decode("ascii")


class HeaderSigner(Signer):
    '''
    Generic object that will sign headers as a dictionary using the http-signature scheme.
    https://github.com/joyent/node-http-signature/blob/master/http_signing.md

    :arg key_id:    the mandatory label indicating to the server which secret to use
    :arg secret:    a PEM-encoded RSA private key or an HMAC secret (must match the algorithm)
    :arg algorithm: one of the six specified algorithms
    :arg headers:   a list of http headers to be included in the signing string, defaulting to ['date'].
    '''
    def __init__(self, key_id, secret, algorithm=None, headers=None):
        if algorithm is None:
            algorithm = DEFAULT_SIGN_ALGORITHM

        super(HeaderSigner, self).__init__(secret=secret, algorithm=algorithm)
        self.headers = headers or ['date']
        self.signature_template = build_signature_template(key_id, algorithm, headers)  # noqa: 405

    def sign(self, headers, host=None, method=None, path=None):
        """
        Add Signature Authorization header to case-insensitive header dict.

        headers is a case-insensitive dict of mutable headers.
        host is a override for the 'host' header (defaults to value in headers).
        method is the HTTP method (required when using '(request-target)').
        path is the HTTP path (required when using '(request-target)').
        """
        headers = CaseInsensitiveDict(headers)  # noqa: 405
        required_headers = self.headers or ['date']
        signable = generate_message(required_headers, headers, host, method, path)  # noqa: 405

        signature = self._sign(signable)
        headers['authorization'] = self.signature_template % signature

        return headers
