# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import threading
import logging
import pprint
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import base64
import json
import oci
from oci._vendor import requests
from .. import auth_utils
from ..certificate_retriever import FileBasedCertificateRetriever
from ..session_key_supplier import SessionKeySupplier
from ..security_token_container import SecurityTokenContainer
from .security_token_signer import SecurityTokenSigner, SECURITY_TOKEN_FORMAT_STRING


class OkeWorkloadIdentityResourcePrincipalSigner(SecurityTokenSigner):

    def __init__(self, sa_token_provider, sa_cert_path, service_host, service_port, region=None, **kwargs):
        self.sa_token_provider = sa_token_provider
        self.sa_cert_path = sa_cert_path
        self.service_host = service_host
        if self.service_host is None:
            raise ValueError("Kubernetes service host was not provided.")
        self.service_port = service_port
        self.region = self._initialize_and_return_region(region)
        self._reset_signers_lock = threading.Lock()

        self.logger = logging.getLogger("{}.{}".format(__name__, id(self)))
        self.logger.addHandler(logging.NullHandler())
        if kwargs.get('log_requests'):
            self.logger.disabled = False
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.disabled = True
        self.requests_session = requests.Session()

        retry_strategy = kwargs.get('retry_strategy', None)
        if retry_strategy:
            self.retry_strategy = retry_strategy
        else:
            self.retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY

        self.proxymux_endpoint = "https://{}:{}/resourcePrincipalSessionTokens".format(self.service_host, self.service_port)
        self.logger.debug("Proxymux endpoint is set to : {} ".format(self.proxymux_endpoint))
        cert_retriever_kwargs = {"certificate_file_path": self.sa_cert_path}
        self.logger.debug("Certificate file path is set to : {} ".format(self.sa_cert_path))
        self.cert_retriever = FileBasedCertificateRetriever(**cert_retriever_kwargs)

        self.session_key_supplier = SessionKeySupplier()
        self.rpst = self.get_security_token()

        if 'generic_headers' in kwargs:
            generic_headers = kwargs['generic_headers']
            super(OkeWorkloadIdentityResourcePrincipalSigner, self).__init__(self.security_token.security_token,
                                                                             self.session_key_supplier.get_key_pair()['private'],
                                                                             generic_headers=generic_headers)
        else:
            super(OkeWorkloadIdentityResourcePrincipalSigner, self).__init__(self.security_token.security_token,
                                                                             self.session_key_supplier.get_key_pair()['private'])

    def _initialize_and_return_region(self, region_raw=None):
        if hasattr(self, 'region'):
            return self.region

        if region_raw is None:
            return None

        # The region should be something like "us-phoenix-1" but if we get "phx" then convert it.
        if region_raw in oci.regions.REGIONS_SHORT_NAMES:
            self.region = oci.regions.REGIONS_SHORT_NAMES[region_raw]
        else:
            self.region = region_raw

        return self.region

    def get_security_token(self):
        """
        Returns the security token. If it is expired, refresh the token.
        """
        if hasattr(self, 'security_token'):
            if self.security_token.valid_with_half_expiration_time():
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
            self.cert_retriever.refresh()
            self.retry_strategy.make_retrying_call(self._get_resource_principal_session_token)
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

    def _get_resource_principal_session_token(self):
        request_payload = {
            "podKey": auth_utils.sanitize_certificate_string(self.session_key_supplier.get_key_pair()['public'].public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
        }

        opc_request_id = auth_utils.generate_opc_request_id()
        sa_token = self.sa_token_provider.get_sa_token()
        headers = {
            "Authorization": "Bearer " + sa_token,
            "Content-type": "application/json",
            "opc-request-id": opc_request_id
        }

        self.logger.debug("Requesting token from : {} ".format(self.proxymux_endpoint))
        response = self.requests_session.post(self.proxymux_endpoint, json=request_payload, headers=headers, verify=self.sa_cert_path, timeout=(10, 60))
        self.logger.debug("Receiving token response......\n{}\n".format(pprint.pformat(
            {"status_code": response.status_code, "url": response.url, "header": dict(response.headers.items()),
             "reason": response.reason}, indent=2)))

        if not response.ok:
            raise oci.exceptions.ServiceError(
                response.status_code,
                response.reason,
                response.headers,
                "Failed to get RPST token from proxymux")

        try:
            decoded_response = base64.b64decode(response.content).decode("UTF-8")
        except ValueError:
            error_text = "Unable to decode the response from auth service ({}): {}. Please contact OKE team for help.".format(self.proxymux_endpoint, response.text)
            raise RuntimeError(error_text)

        if 'token' in decoded_response:
            response_json = json.loads(decoded_response)
            self.security_token = SecurityTokenContainer(self.session_key_supplier, response_json['token'][3:])
        else:
            error_text = "Could not find token in the decoded response from auth service ({}): {}.".format(self.proxymux_endpoint, decoded_response)
            raise RuntimeError(error_text)
