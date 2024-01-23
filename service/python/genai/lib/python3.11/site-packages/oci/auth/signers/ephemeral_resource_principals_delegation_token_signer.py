# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .ephemeral_resource_principals_signer import EphemeralResourcePrincipalSigner


class EphemeralResourcePrincipalsDelegationTokenSigner(EphemeralResourcePrincipalSigner):
    """
       This signer takes the following parameters:
        - session_token
        - private_key
        - private_key_passphrase

            These three parameters may be used in one of two modes. In the first mode, they contain the actual
            contents of the Resource Pricipals Session Token, private key (in PEM format) and the passphrase. This mode is only useful for
            short-lived programs.

            In the second mode, if these parameters contain absolute paths, then those paths are taken as the
            on-filesystem location of the values in question. The signer may attempt to reload these values from
            the filesystem on receiving a 401 response from an OCI service. This mode is used in cases where the
            program executes in an environment where an external provider may inject updated tokens into
            the filesystem.

        - region: the canonical region name
            This is utilised in locating the "local" endpoints of services.

        - delegation_token : The Delegation token to be used for signing the request.

    """

    def __init__(self, **kwargs):
        self.delegation_token = kwargs['delegation_token']
        generic_headers = ["date", "(request-target)", "host", "opc-obo-token"]
        super(EphemeralResourcePrincipalsDelegationTokenSigner, self).__init__(generic_headers=generic_headers, **kwargs)

    # opc-obo-token is added to the request headers
    def do_request_sign(self, request, enforce_content_headers=True):
        request.headers['opc-obo-token'] = self.delegation_token
        super(EphemeralResourcePrincipalsDelegationTokenSigner, self).do_request_sign(request, enforce_content_headers)
        return request
