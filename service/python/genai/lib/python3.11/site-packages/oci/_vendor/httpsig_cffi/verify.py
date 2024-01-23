# coding: utf-8
# Modified Work: Copyright (c) 2018, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.
# Original Work: Copyright (c) 2014 Adam Knight
# Original Work: Copyright (c) 2012 Adam T. Lindsay (original author)

"""
Module to assist in verifying a signed header.
"""
from oci._vendor import six

from cryptography.hazmat.backends import default_backend  # noqa: 401
from cryptography.hazmat.primitives import hashes, hmac, serialization  # noqa: 401
from cryptography.hazmat.primitives.asymmetric import rsa, padding  # noqa: 401
from cryptography.exceptions import InvalidSignature  # noqa: 401

from base64 import b64decode

from .sign import Signer
from .utils import *  # noqa: 403


class Verifier(Signer):
    """
    Verifies signed text against a secret.
    For HMAC, the secret is the shared secret.
    For RSA, the secret is the PUBLIC key.
    """
    def _verify(self, data, signature):
        """
        Verifies the data matches a signed version with the given signature.
        `data` is the message to verify
        `signature` is a base64-encoded signature to verify against `data`
        """

        if isinstance(data, six.string_types):
            data = data.encode("ascii")
        if isinstance(signature, six.string_types):
            signature = signature.encode("ascii")

        if self.sign_algorithm == 'rsa':
            try:
                self._rsa_public.verify(
                    b64decode(signature),
                    data,
                    padding.PKCS1v15(),
                    self._rsahash()
                )
                return True
            except InvalidSignature:
                return False
        elif self.sign_algorithm == 'hmac':
            h = self._sign_hmac(data)
            s = b64decode(signature)
            return (h == s)
        else:
            raise HttpSigException("Unsupported algorithm.")  # noqa: 405


class HeaderVerifier(Verifier):
    """
    Verifies an HTTP signature from given headers.
    """
    def __init__(self, headers, secret, required_headers=None, method=None, path=None, host=None):
        """
        Instantiate a HeaderVerifier object.

        :param headers:             A dictionary of headers from the HTTP request.
        :param secret:              The HMAC secret or RSA *public* key.
        :param required_headers:    Optional. A list of headers required to be present to validate, even if the signature is otherwise valid.  Defaults to ['date'].
        :param method:              Optional. The HTTP method used in the request (eg. "GET"). Required for the '(request-target)' header.
        :param path:                Optional. The HTTP path requested, exactly as sent (including query arguments and fragments). Required for the '(request-target)' header.
        :param host:                Optional. The value to use for the Host header, if not supplied in :param:headers.
        """
        required_headers = required_headers or ['date']

        auth = parse_authorization_header(headers['authorization'])  # noqa: 405
        if len(auth) == 2:
            self.auth_dict = auth[1]
        else:
            raise HttpSigException("Invalid authorization header.")  # noqa: 405

        self.headers = CaseInsensitiveDict(headers)  # noqa: 405
        self.required_headers = [s.lower() for s in required_headers]
        self.method = method
        self.path = path
        self.host = host

        super(HeaderVerifier, self).__init__(secret, algorithm=self.auth_dict['algorithm'])

    def verify(self):
        """
        Verify the headers based on the arguments passed at creation and current properties.

        Raises an Exception if a required header (:param:required_headers) is not found in the signature.
        Returns True or False.
        """
        auth_headers = self.auth_dict.get('headers', 'date').split(' ')

        if len(set(self.required_headers) - set(auth_headers)) > 0:
            raise Exception('{} is a required header(s)'.format(', '.join(set(self.required_headers) - set(auth_headers))))

        signing_str = generate_message(auth_headers, self.headers, self.host, self.method, self.path)  # noqa: 405

        return self._verify(signing_str, self.auth_dict['signature'])
