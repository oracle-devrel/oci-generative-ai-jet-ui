# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .resource_principals_federation_signer import ResourcePrincipalsFederationSigner


class ResourcePrincipalsDelegationTokenSigner(ResourcePrincipalsFederationSigner):
    """
        ResourcePrincipalsDelegationTokenSigner extends the functionality of ResourcePrincipalsFederationSigner.
        A delegation token allows the instance to assume the privileges of the user for which the token
        was created.

        :param resource_principal_token_endpoint: The endpoint that can provide the resource principal token.
                                                  This is a service endpoint.

        :param resource_principal_session_token_endpoint: The endpoint that can provide the resource principal session
                                                          token. This will default to the auth federation endpoint
                                                          if not provided.

        :param resource_principal_token_path_provider: An object of a class which implements RptPathProviderInterface
                                                       that can provide the path for resource principal token.
                                                       If not set, use DefaultRptPathProvider to determine the path.

        :param delegation_token : The Delegation token to be used for signing the request.

    """

    def __init__(self, **kwargs):
        self.delegation_token = kwargs['delegation_token']
        generic_headers = ["date", "(request-target)", "host", "opc-obo-token"]
        super(ResourcePrincipalsDelegationTokenSigner, self).__init__(generic_headers=generic_headers, **kwargs)

    # opc-obo-token is added to the request headers
    def do_request_sign(self, request, enforce_content_headers=True):
        request.headers['opc-obo-token'] = self.delegation_token
        super(ResourcePrincipalsDelegationTokenSigner, self).do_request_sign(request, enforce_content_headers)
        return request
