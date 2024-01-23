# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import json
import threading
import oci
from .instance_principals_security_token_signer import InstancePrincipalsSecurityTokenSigner
from .security_token_signer import SecurityTokenSigner, SECURITY_TOKEN_FORMAT_STRING
from ..security_token_container import SecurityTokenContainer
from ..session_key_supplier import SessionKeySupplier
from .. import auth_utils
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from ..rpt_path_providers import DefaultRptPathProvider


class ResourcePrincipalsFederationSigner(SecurityTokenSigner):
    METADATA_AUTH_HEADERS = {'Authorization': 'Bearer Oracle'}

    def __init__(self, resource_principal_token_endpoint=None, resource_principal_session_token_endpoint=None,
                 resource_principal_token_path_provider=None, retry_strategy=None, log_requests=None,
                 generic_headers=None, **kwargs):
        """
        :param resource_principal_token_endpoint: The endpoint that can provide the resource principal token.  This is
                                                  a service endpoint.
        :param resource_principal_session_token_endpoint: The endpoint that can provide the resource principal session token.
                                                          This will default to the auth federation endpoint if not provided.
        :param resource_principal_token_path_provider: An object of a class which implements RptPathProviderInterface that can provide the
                                                        path for resource principal token. If not set, use
                                                        DefaultRptPathProvider to determine the path
        """
        self.resource_principal_token_path_provider = resource_principal_token_path_provider or DefaultRptPathProvider(**kwargs)
        self.resource_principal_token_path = self.resource_principal_token_path_provider.get_path()

        self._reset_signers_lock = threading.Lock()
        if resource_principal_token_endpoint:
            self.resource_principal_token_endpoint = resource_principal_token_endpoint
        else:
            raise ValueError("resource_principal_token_endpoint must be provided")

        self.instance_principal_signer = InstancePrincipalsSecurityTokenSigner(log_requests=log_requests)
        self.session_key_supplier = SessionKeySupplier()
        self.region = self.instance_principal_signer.initialize_and_return_region()
        self.tenancy_id = self.instance_principal_signer.tenancy_id

        if resource_principal_session_token_endpoint:
            self.resource_principal_session_token_endpoint = resource_principal_session_token_endpoint
        else:
            self.resource_principal_session_token_endpoint = oci.regions.endpoint_for('auth', self.region)

        if retry_strategy:
            self.retry_strategy = retry_strategy
        else:
            self.retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY

        # Holders for the tokens needed.
        self.rpt = None
        self.spst = None

        # Setup the base_client for calls to Service to get Resource Principal Token
        # and Service Principal Sesion Token

        # The config is not needed by when using the instance principals signer, but request logging could be enabled.
        config = {}
        if log_requests:
            config["log_requests"] = log_requests

        self.base_client = oci.BaseClient("",  # No service
                                          config,
                                          self.instance_principal_signer,
                                          {},  # No type mapping
                                          region_client=False,
                                          service_endpoint=self.resource_principal_token_endpoint)

        # Get the Resource Principal Session Token and use it to set up the signer
        self.rpst = self.get_security_token()
        if generic_headers:
            super(ResourcePrincipalsFederationSigner, self).__init__(self.rpst, self.session_key_supplier.get_key_pair()['private'], generic_headers=generic_headers)
        else:
            super(ResourcePrincipalsFederationSigner, self).__init__(self.rpst, self.session_key_supplier.get_key_pair()['private'])

    def get_security_token(self):
        """
        Returns the security token. If it is expired, refresh the token.
        """
        if hasattr(self, 'security_token'):
            if self.security_token.valid_with_jitter():
                return self.security_token.security_token

        return self._refresh_security_token_inner()

    def refresh_security_token(self):
        """
        Refresh the security token
        """
        return self._refresh_security_token_inner()

    def _refresh_security_token_inner(self):
        self._reset_signers_lock.acquire()
        try:
            self.session_key_supplier.refresh()
            self.instance_principal_signer.refresh_security_token()

            # Get RPT blob, Service Principal Session Token from service, Steps A.1 and B.1
            self.rpt, self.spst = self._get_resource_principal_token_and_service_principal_session_token()

            # Get RPST token from itentity, steps A.2 and B.2
            self.security_token = SecurityTokenContainer(self.session_key_supplier, self._get_resource_principal_session_token())
            self._reset_signers()
            return self.security_token.security_token
        finally:
            self._reset_signers_lock.release()

    def _reset_signers(self):
        self.api_key = SECURITY_TOKEN_FORMAT_STRING.format(self.security_token.security_token)
        self.private_key = self.session_key_supplier.get_key_pair()['private']

        if hasattr(self, '_basic_signer'):
            self._basic_signer.reset_signer(self.api_key, self.private_key)
        if hasattr(self, '_body_signer'):
            self._body_signer.reset_signer(self.api_key, self.private_key)

    def _get_resource_principal_token_and_service_principal_session_token(self):
        """
        Get the Resource Principal Token and the Service Principal Session Token

        This makes a call to the resource_principal_token_endpoint which is
        defined by the service.
        """
        method = "get"
        self.base_client.endpoint = self.resource_principal_token_endpoint

        response = self.make_call(method, self.resource_principal_token_path)
        parsed_response = json.loads(response.data.decode('UTF-8'))
        return parsed_response['resourcePrincipalToken'], parsed_response['servicePrincipalSessionToken']

    def _get_resource_principal_session_token(self):
        """
        Get the Resource Principal Session Token
        """
        method = "post"
        resource_path = "/v1/resourcePrincipalSessionToken"

        self.base_client.endpoint = self.resource_principal_session_token_endpoint

        public_key = self.session_key_supplier.get_key_pair()['public']
        sanitized_public_key = auth_utils.sanitize_certificate_string(public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))

        request_payload = {
            'resourcePrincipalToken': self.rpt,
            'servicePrincipalSessionToken': self.spst,
            'sessionPublicKey': sanitized_public_key
        }

        # The base client will convert the payload to JSON, but won't update the content length, so we need to
        # it here.
        json_request_payload = json.dumps(request_payload)
        header_params = {'content-type': 'application/json',
                         'Content-Length': str(len(json_request_payload))}
        response = self.make_call(method, resource_path, header_params=header_params, body=request_payload)
        parsed_response = json.loads(response.data.decode('UTF-8'))

        return parsed_response['token']

    def make_call(self, method, resource_path, path_params=None, header_params=None, body=None):
        """
        make_call

        Normally this would be part of the generated client.  In this case the endpoint for the
        Resource Principal Token is not part of the generated client, so we need the same
        behavior here.
        """
        if self.retry_strategy:
            return self.retry_strategy.make_retrying_call(
                self.base_client.call_api,
                resource_path=resource_path,
                method=method,
                path_params=path_params,
                header_params=header_params,
                body=body,
                response_type=oci.base_client.BYTES_RESPONSE_TYPE)
        else:
            return self.base_client.call_api(
                resource_path=resource_path,
                method=method,
                path_params=path_params,
                header_params=header_params,
                body=body,
                response_type=oci.base_client.BYTES_RESPONSE_TYPE)
