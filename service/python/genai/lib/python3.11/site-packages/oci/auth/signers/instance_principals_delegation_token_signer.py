# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .instance_principals_security_token_signer import InstancePrincipalsSecurityTokenSigner


class InstancePrincipalsDelegationTokenSigner(InstancePrincipalsSecurityTokenSigner):
    """
    InstancePrincipalsDelegationTokenSigner extends the functionality of InstancePrincipalsSecurityTokenSigner.
    A delegation token allows the instance to assume the privileges of the user for which the token
    was created.

    This signer can be used as follows:

    .. code-block:: python

        import oci

        signer = oci.auth.signers.InstancePrincipalsDelegationTokenSigner(delegation_token=delegation_token)
        identity_client = oci.identity.IdentityClient(config={}, signer=signer)
        regions = identity_client.list_regions()

    :param str delegation_token (required)
        This token allows an instance to assume the privileges of a specific user
        and act on-behalf-of that user.

    :param str federation_endpoint: (optional)
        Users of this class can specify an explicit federation_endpoint, representing the Auth Service endpoint from which to retrieve a security token. If it is not
        provided then we will construct an endpoint based on the region we read from the metadata endpoint for the instance

    :param federation_client_cert_bundle_verify: (optional)
        If we need a specific cert bundle in order to perform verification against the federation endpoint, this parameter is the path to that bundle. Alternatively,
        False can be passed to disable verification.
    :type federation_client_cert_bundle_verify: str or Boolean

    :param obj federation_client_retry_strategy: (optional):
        A retry strategy to apply to calls made by the X509FederationClient used by this class. This should be one of the strategies available in
        the :py:mod:`~oci.retry` module. A convenience :py:data:`~oci.retry.DEFAULT_RETRY_STRATEGY` is also available and
        will be used by the X509FederationClient if no explicit retry strategy is specified.

        The specifics of the default retry strategy are described `here <https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/sdk_behaviors/retries.html>`__.

        To have this operation explicitly not perform any retries, pass an instance of :py:class:`~oci.retry.NoneRetryStrategy`.
    """

    # opc-obo-token is added to the generic_headers list
    def __init__(self, **kwargs):
        self.delegation_token = kwargs['delegation_token']
        generic_headers = ["date", "(request-target)", "host", "opc-obo-token"]
        super(InstancePrincipalsDelegationTokenSigner, self).__init__(generic_headers=generic_headers, **kwargs)

    def do_request_sign(self, request, enforce_content_headers=True):
        """
        Signs the request with the opc-obo-token added to the request header
        """
        request.headers['opc-obo-token'] = self.delegation_token
        super(InstancePrincipalsDelegationTokenSigner, self).do_request_sign(request, enforce_content_headers)
        return request
