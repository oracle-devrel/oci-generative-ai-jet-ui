# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .security_token_signer import X509FederationClientBasedSecurityTokenSigner
from ..certificate_retriever import UrlBasedCertificateRetriever, INSTANCE_METADATA_URL_CERTIFICATE_RETRIEVER_RETRY_STRATEGY
from ..session_key_supplier import SessionKeySupplier
from ..federation_client import X509FederationClient
from .. import auth_utils
from oci._vendor import requests
from oci._vendor.requests.exceptions import HTTPError
from oci._vendor.requests.exceptions import ConnectTimeout

import oci.regions
import logging


class InstancePrincipalsSecurityTokenSigner(X509FederationClientBasedSecurityTokenSigner):
    """
    A SecurityTokenSigner which uses a security token for an instance principal.  This signer can also
    refresh its token as needed.

    This signer is self-sufficient in that its internals know how to source the required information to request and use
    the token:

    * Using the metadata endpoint for the instance (http://169.254.169.254/opc/v2) we can discover the region the instance is in, its leaf certificate and any intermediate certificates (for requesting the token) and the tenancy (as) that is in the leaf certificate.
    * The signer leverages X509FederationClient so it can refresh the security token and also get the private key needed to sign requests (via the client's session_key_supplier)

    This signer can be used as follows:

    .. code-block:: python

        import oci

        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        identity_client = oci.identity.IdentityClient(config={}, signer=signer)
        regions = identity_client.list_regions()

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

        The specifics of the default retry strategy are described `here <https://docs.oracle.com/en-us/iaas/tools/python/latest/sdk_behaviors/retries.html>`__.

        To have this operation explicitly not perform any retries, pass an instance of :py:class:`~oci.retry.NoneRetryStrategy`.

    :param bool log_requests: (optional)
        log_request if set to True, will log the request url and response data when retrieving
        the certificate & corresponding private key (if there is one defined for this retriever) from UrlBasedCertificateRetriever,
        region, federation endpoint, and the response for receiving the token from the federation endpoint
    """

    METADATA_URL_BASE = 'http://169.254.169.254/opc/v2'
    GET_REGION_URL = '{}/instance/region'.format(METADATA_URL_BASE)
    LEAF_CERTIFICATE_URL = '{}/identity/cert.pem'.format(METADATA_URL_BASE)
    LEAF_CERTIFICATE_PRIVATE_KEY_URL = '{}/identity/key.pem'.format(METADATA_URL_BASE)
    INTERMEDIATE_CERTIFICATE_URL = '{}/identity/intermediate.pem'.format(METADATA_URL_BASE)
    METADATA_AUTH_HEADERS = {'Authorization': 'Bearer Oracle'}

    def __init__(self, **kwargs):
        self.logger = logging.getLogger("{}.{}".format(__name__, id(self)))
        self.logger.addHandler(logging.NullHandler())
        if kwargs.get('log_requests'):
            self.logger.disabled = False
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.disabled = True

        # If user sends in custom retry strategy use that, else use INSTANCE_METADATA_URL_CERTIFICATE_RETRIEVER_RETRY_STRATEGY
        if kwargs.get('retry_strategy'):
            self.retry_strategy = kwargs['retry_strategy']
        else:
            self.retry_strategy = INSTANCE_METADATA_URL_CERTIFICATE_RETRIEVER_RETRY_STRATEGY

        try:
            self.leaf_certificate_retriever = UrlBasedCertificateRetriever(
                certificate_url=self.LEAF_CERTIFICATE_URL,
                private_key_url=self.LEAF_CERTIFICATE_PRIVATE_KEY_URL,
                retry_strategy=self.retry_strategy,
                headers=self.METADATA_AUTH_HEADERS,
                log_requests=kwargs.get('log_requests'))
        except (HTTPError, ConnectTimeout) as e:
            if e.response and e.response.status_code == 404:
                InstancePrincipalsSecurityTokenSigner.METADATA_URL_BASE = 'http://169.254.169.254/opc/v1'
                InstancePrincipalsSecurityTokenSigner.GET_REGION_URL = '{}/instance/region'.format(InstancePrincipalsSecurityTokenSigner.METADATA_URL_BASE)
                InstancePrincipalsSecurityTokenSigner.LEAF_CERTIFICATE_URL = '{}/identity/cert.pem'.format(InstancePrincipalsSecurityTokenSigner.METADATA_URL_BASE)
                InstancePrincipalsSecurityTokenSigner.LEAF_CERTIFICATE_PRIVATE_KEY_URL = '{}/identity/key.pem'.format(InstancePrincipalsSecurityTokenSigner.METADATA_URL_BASE)
                InstancePrincipalsSecurityTokenSigner.INTERMEDIATE_CERTIFICATE_URL = '{}/identity/intermediate.pem'.format(InstancePrincipalsSecurityTokenSigner.METADATA_URL_BASE)
                self.leaf_certificate_retriever = UrlBasedCertificateRetriever(
                    certificate_url=self.LEAF_CERTIFICATE_URL,
                    private_key_url=self.LEAF_CERTIFICATE_PRIVATE_KEY_URL,
                    retry_strategy=self.retry_strategy,
                    headers=self.METADATA_AUTH_HEADERS)
            else:
                if not e.args:
                    e.args = ('',)
                e.args = e.args + ("Instance principals authentication can only be used on OCI compute instances. Please confirm this code is running on an OCI compute instance. See https://docs.oracle.com/en-us/iaas/Content/Identity/Tasks/callingservicesfrominstances.htm for more info.",)
                raise e

        self.intermediate_certificate_retriever = UrlBasedCertificateRetriever(
            certificate_url=self.INTERMEDIATE_CERTIFICATE_URL,
            retry_strategy=self.retry_strategy,
            headers=self.METADATA_AUTH_HEADERS)
        self.session_key_supplier = SessionKeySupplier()
        self.tenancy_id = auth_utils.get_tenancy_id_from_certificate(self.leaf_certificate_retriever.get_certificate_as_certificate())
        self.initialize_and_return_region()

        if 'federation_endpoint' in kwargs and kwargs['federation_endpoint']:
            federation_endpoint = kwargs['federation_endpoint']
        else:
            federation_endpoint = '{}/v1/x509'.format(oci.regions.endpoint_for('auth', self.region))

        self.logger.debug("federation endpoint is set to : %s " % (federation_endpoint))

        federation_client = X509FederationClient(
            federation_endpoint=federation_endpoint,
            tenancy_id=self.tenancy_id,
            session_key_supplier=self.session_key_supplier,
            leaf_certificate_retriever=self.leaf_certificate_retriever,
            intermediate_certificate_retrievers=[self.intermediate_certificate_retriever],
            cert_bundle_verify=kwargs.get('federation_client_cert_bundle_verify', None),
            retry_strategy=kwargs.get('federation_client_retry_strategy', None),
            purpose=kwargs.get('purpose', None),
            log_requests=kwargs.get('log_requests')
        )
        if 'generic_headers' in kwargs:
            generic_headers = kwargs['generic_headers']
            super(InstancePrincipalsSecurityTokenSigner, self).__init__(federation_client=federation_client, generic_headers=generic_headers)
        else:
            super(InstancePrincipalsSecurityTokenSigner, self).__init__(federation_client)

    def initialize_and_return_region(self):
        if hasattr(self, 'region'):
            return self.region

        self.logger.debug("Requesting region information from : %s " % (self.GET_REGION_URL))
        response = requests.get(self.GET_REGION_URL, timeout=(10, 60), headers=self.METADATA_AUTH_HEADERS)
        region_raw = response.text.strip().lower()

        # The region can be something like "phx" but internally we expect "us-phoenix-1", "us-ashburn-1" etc.
        if region_raw in oci.regions.REGIONS_SHORT_NAMES:
            self.region = oci.regions.REGIONS_SHORT_NAMES[region_raw]
        else:
            self.region = region_raw

        self.logger.debug("Region is set to : %s " % (self.region))
        return self.region
