# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import oci.signer
import threading


SECURITY_TOKEN_FORMAT_STRING = 'ST${}'


class SecurityTokenSigner(oci.signer.AbstractBaseSigner):
    """
    The base signer for signing requests where the API key is a token (e.g. instance principals, service-to-service auth) rather representing
    the details for a specific user.

    This class expects caller to provide the token and the private key whose corresponding public key was provided when requesting the token.
    The headers to sign are also customizable but they default to:

        - date, (request-target), host as generic headers on each request
        - content-length, content-type and x-content-sha256 on as additional headers requests with bodies


    """

    def __init__(self, token, private_key, generic_headers=["date", "(request-target)", "host"], body_headers=["content-length", "content-type", "x-content-sha256"]):
        self.api_key = SECURITY_TOKEN_FORMAT_STRING.format(token)
        self.private_key = private_key

        self.create_signers(self.api_key, self.private_key, generic_headers, body_headers)


class X509FederationClientBasedSecurityTokenSigner(SecurityTokenSigner):
    """
    A SecurityTokenSigner where the token and private key are sourced from a provided X509FederationClient. The token is retrieved via the client's get_security_token()
    method, and the private key is retrieved by reading it from the session_key_supplier in the client.

    The headers to sign are also customizable but they default to:

        - date, (request-target), host as generic headers on each request
        - content-length, content-type and x-content-sha256 on as additional headers requests with bodies


    """

    def __init__(self, federation_client, generic_headers=["date", "(request-target)", "host"], body_headers=["content-length", "content-type", "x-content-sha256"]):
        self.federation_client = federation_client
        self._reset_signers_lock = threading.Lock()

        super(X509FederationClientBasedSecurityTokenSigner, self).__init__(
            self.federation_client.get_security_token(),
            self.federation_client.session_key_supplier.get_key_pair()['private'],
            generic_headers=generic_headers,
            body_headers=body_headers
        )

    def __call__(self, request, enforce_content_headers=True):
        self._reset_signers()
        return super(X509FederationClientBasedSecurityTokenSigner, self).__call__(request, enforce_content_headers)

    def refresh_security_token(self):
        """
        Refresh the security token
        """
        self.federation_client.refresh_security_token()

    def _reset_signers(self):
        self._reset_signers_lock.acquire()
        try:
            refreshed_token = self.federation_client.get_security_token()
            self.api_key = SECURITY_TOKEN_FORMAT_STRING.format(refreshed_token)
            self.private_key = self.federation_client.session_key_supplier.get_key_pair()['private']

            self._basic_signer.reset_signer(self.api_key, self.private_key)
            self._body_signer.reset_signer(self.api_key, self.private_key)
        finally:
            self._reset_signers_lock.release()
