# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import json
import os
import threading
import logging

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import oci
import oci.signer

from .ephemeral_resource_principals_signer import FixedSessionKeySupplier, FileBasedSessionKeySupplier
from .key_pair_signer import KeyPairSigner
from .security_token_signer import SecurityTokenSigner, SECURITY_TOKEN_FORMAT_STRING
from .. import auth_utils
from ..security_token_container import SecurityTokenContainer


class EphemeralResourcePrincipalV21Signer(SecurityTokenSigner):

    def __init__(self, resource_principal_token_endpoint=None, resource_principal_session_token_endpoint=None,
                 resource_id=None, private_key=None, private_key_passphrase=None, retry_strategy=None,
                 log_requests=None, generic_headers=None, tenancy_id=None, rp_version=None, region=None, **kwargs):
        self.logger = logging.getLogger(f"{__name__}.{id(self)}")
        if resource_principal_token_endpoint:
            self.resource_principal_token_endpoint = resource_principal_token_endpoint
        else:
            raise ValueError("resource_principal_token_endpoint must be provided")

        if resource_principal_session_token_endpoint:
            self.resource_principal_session_token_endpoint = resource_principal_session_token_endpoint
        else:
            raise ValueError("resource_principal_session_token_endpoint must be provided")

        if resource_id is None:
            raise ValueError("resource_id should be provided")

        if private_key is None:
            raise ValueError("private_key should be provided")

        if kwargs.get("rp_version") == "2.1.1" and tenancy_id is None:
            raise ValueError("tenancy_id should be provided")

        self._reset_signers_lock = threading.Lock()
        self.region = self._initialize_and_return_region(region_raw=region)

        if retry_strategy:
            self.retry_strategy = retry_strategy
        else:
            self.retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY

        # Hard coded Path for RPT
        self.resource_principal_token_path = f"/20180711/resourcePrincipalTokenV2/{resource_id}"

        # Holders for the tokens needed.
        self.rpt = None
        self.spst = None

        # Setup the base_client for calls to Service to get Resource Principal Token and Service Principal Session Token
        # The config is not needed but request logging could be enabled.
        config = {}
        if log_requests:
            config["log_requests"] = log_requests

        self.base_client = oci.BaseClient("",  # No service
                                          config,
                                          KeyPairSigner(rp_version, resource_id, tenancy_id, private_key, private_key_passphrase),
                                          {},  # No type mapping
                                          region_client=False,
                                          service_endpoint=self.resource_principal_token_endpoint)
        # Set Key Supplier
        self.session_key_supplier = self.construct_session_key_supplier(private_key, private_key_passphrase)

        # Get the Resource Principal Session Token and use it to set up the signer
        self.rpst = self.get_security_token()
        if generic_headers:
            super(EphemeralResourcePrincipalV21Signer, self).__init__(self.security_token.security_token,
                                                                      self.session_key_supplier.get_key_pair()['private'],
                                                                      generic_headers=generic_headers)
        else:
            super(EphemeralResourcePrincipalV21Signer, self).__init__(self.security_token.security_token,
                                                                      self.session_key_supplier.get_key_pair()['private'])

    def construct_session_key_supplier(self, private_key=None, private_key_passphrase=None):
        if private_key is None:
            raise ValueError("private_key must be provided")
        passphrase = private_key_passphrase
        if os.path.isabs(private_key):
            return FileBasedSessionKeySupplier(private_key, passphrase)
        else:
            return FixedSessionKeySupplier(oci.signer.load_private_key(private_key, passphrase))

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

            # Get RPT blob, Service Principal Session Token from service, Steps A.1 and B.1
            self.rpt, self.spst = self._get_resource_principal_token_and_service_principal_session_token()

            # Get RPST token from identity, steps A.2 and B.2
            self.security_token = SecurityTokenContainer(self.session_key_supplier,
                                                         self._get_resource_principal_session_token())
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
        sanitized_public_key = auth_utils.sanitize_certificate_string(
            public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))

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

    def _initialize_and_return_region(self, region_raw=None):
        if hasattr(self, 'region'):
            return self.region

        # The region can be something like "phx" but internally we expect "us-phoenix-1", "us-ashburn-1" etc.
        if region_raw in oci.regions.REGIONS_SHORT_NAMES:
            region_to_use = oci.regions.REGIONS_SHORT_NAMES[region_raw]
        else:
            region_to_use = region_raw

        self.logger.debug("Region is set to: {}".format(region_to_use))
        return region_to_use
