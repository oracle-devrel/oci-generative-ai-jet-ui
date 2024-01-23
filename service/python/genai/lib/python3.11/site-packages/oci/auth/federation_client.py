# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from . import auth_utils
from .security_token_container import SecurityTokenContainer
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.hashes import SHA1

from oci._vendor import requests

import oci.retry
import oci.signer
import threading
import logging
import pprint


class X509FederationClient(object):
    REQUIRED_INIT_KWARGS = [
        'federation_endpoint',
        'tenancy_id',
        'session_key_supplier',
        'leaf_certificate_retriever'
    ]

    def __init__(self, **kwargs):
        """
        A client which can be used to retrieve a token from Auth Service. It needs the following supplied to it:

            - The endpoint for Auth Service
            - Our tenancy OCID
            - A session key supplier so that we can send its public key as part of the token request. The private key
            in the session key supplier should be used to sign all requests made with the token
            - The certificate (via leaf_certificate_retriever) which will be used to sign the requests to Auth Service.

        Optionally, intermediate certificates (if present) can be supplied as part of the request to Auth Service.

        The client has knowledge of its last requested token and can re-request the token if it is expired (otherwise
        it will vend the last requested token if it is not expired).

        :param str federation_endpoint:
            The Auth Service endpoint from which to retrieve the token.

        :param str tenancy_id:
            The OCID of the tenancy whose resources will be interacted with by users of the token.

        :param SessionKeySupplier session_key_supplier:
            A SessionKeySupplier that can vend a public and private key. The public key will be sent as part of the token
            request and the private key should be used to sign all requests made with the token vended by this client.

        :param CertificateRetriever leaf_certificate_retriever:
            The certificate which will be used to sign requests to Auth Service.

        :param list[CertificateRetriever] intermediate_certificate_retrievers: (optional)
            A list of retrievers which can be used to fetch intermediate certificates which can be sent as part of the Auth Service request. This is an optional parameter

        :param cert_bundle_verify: (optional)
            If we need a specific cert bundle in order to perform verification against the federation endpoint, this parameter is the path to that bundle. Alternatively,
            False can be passed to disable verification.
        :type cert_bundle_verify: str or Boolean

        :param obj retry_strategy: (optional)
            A retry strategy to apply to calls made by this client. This should be one of the strategies available in
            the :py:mod:`~oci.retry` module. A convenience :py:data:`~oci.retry.DEFAULT_RETRY_STRATEGY` is also available and
            will be used if no explicit retry strategy is specified.

            The specifics of the default retry strategy are described `here <https://docs.oracle.com/en-us/iaas/tools/python/latest/sdk_behaviors/retries.html>`__.

            To have this operation explicitly not perform any retries, pass an instance of :py:class:`~oci.retry.NoneRetryStrategy`.

        :param bool log_requests: (optional)
        log_request if set to True, will log the request url and response data when retrieving
        the token from the federation endpoint.
        """

        kwarg_keys = kwargs.keys()
        missing_keys = []

        for required in self.REQUIRED_INIT_KWARGS:
            if required not in kwarg_keys:
                missing_keys.append(required)
            elif not kwargs[required]:
                missing_keys.append(required)

        if missing_keys:
            raise TypeError('The following required arguments were not provided: {}'.format(', '.join(missing_keys)))

        self.federation_endpoint = kwargs['federation_endpoint']
        self.tenancy_id = kwargs['tenancy_id']
        self.session_key_supplier = kwargs['session_key_supplier']
        self.leaf_certificate_retriever = kwargs['leaf_certificate_retriever']

        # The default (instance principal) purpose is None
        self.purpose = None
        if 'purpose' in kwargs and kwargs['purpose'] is not None:
            self.purpose = kwargs['purpose']

        self.logger = logging.getLogger("{}.{}".format(__name__, id(self)))
        self.logger.addHandler(logging.NullHandler())
        if kwargs.get('log_requests'):
            self.logger.disabled = False
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.disabled = True

        if 'intermediate_certificate_retrievers' in kwargs and kwargs['intermediate_certificate_retrievers']:
            self.intermediate_certificate_retrievers = kwargs['intermediate_certificate_retrievers']
        else:
            self.intermediate_certificate_retrievers = []

        self.cert_bundle_verify = kwargs.get('cert_bundle_verify', None)
        self._refresh_lock = threading.Lock()

        retry_strategy = kwargs.get('retry_strategy', None)
        if retry_strategy:
            self.retry_strategy = retry_strategy
        else:
            self.retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY

        self.requests_session = requests.Session()

    def refresh_security_token(self):
        return self._refresh_security_token_inner()

    def get_security_token(self):
        if hasattr(self, 'security_token'):
            if self.security_token.valid_with_jitter():
                return self.security_token.security_token

        return self._refresh_security_token_inner()

    def _refresh_security_token_inner(self):
        self._refresh_lock.acquire()
        try:
            self.session_key_supplier.refresh()
            self.leaf_certificate_retriever.refresh()
            # for the default (instance principal) purpose, verify tenancy id matches
            if self.purpose is None:
                updated_tenancy_id = auth_utils.get_tenancy_id_from_certificate(self.leaf_certificate_retriever.get_certificate_as_certificate())
                if updated_tenancy_id != self.tenancy_id:
                    raise RuntimeError('Unexpected update of tenancy OCID in the leaf certificate. Previous tenancy: {}, Updated: {}'.format(self.tenancy_id, updated_tenancy_id))

            for retriever in self.intermediate_certificate_retrievers:
                retriever.refresh()

            self.retry_strategy.make_retrying_call(self._get_security_token_from_auth_service)
            return self.security_token.security_token
        finally:
            self._refresh_lock.release()

    def _get_security_token_from_auth_service(self):
        request_payload = {
            'certificate': auth_utils.sanitize_certificate_string(self.leaf_certificate_retriever.get_certificate_raw()),
            'publicKey': auth_utils.sanitize_certificate_string(self.session_key_supplier.get_key_pair()['public'].public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
        }
        # The default (instance principal) purpose is None
        if self.purpose is not None:
            request_payload['purpose'] = self.purpose

        if self.intermediate_certificate_retrievers:
            retrieved_certs = []
            for retriever in self.intermediate_certificate_retrievers:
                retrieved_certs.append(auth_utils.sanitize_certificate_string(retriever.get_certificate_raw()))

            request_payload['intermediateCertificates'] = retrieved_certs

        certificate = self.leaf_certificate_retriever.get_certificate_as_certificate()
        fingerprint = ":".join("{:02X}".format(ch) for ch in bytearray(certificate.fingerprint(SHA1())))
        signer = AuthTokenRequestSigner(self.tenancy_id, fingerprint, self.leaf_certificate_retriever)

        self.logger.debug("Requesting token from : %s " % (self.federation_endpoint))
        response = self.requests_session.post(self.federation_endpoint, json=request_payload, auth=signer, verify=self.cert_bundle_verify, timeout=(10, 60))
        self.logger.debug("Receiving token response......\n{}\n".format(pprint.pformat(
            {"status_code": response.status_code, "url": response.url, "header": dict(response.headers.items()),
                "reason": response.reason}, indent=2)))

        parsed_response = None
        try:
            parsed_response = response.json()
        except ValueError:
            error_text = 'Unable to parse response from auth service ({}): {}'.format(self.federation_endpoint, response.text)

            # If the response was a 2xx but unparseable, raise it straight away because it implies a potential service issue. If
            # we have a non-2xx but it is not parseable that is a more ambiguous scenario (e.g. could have been an issue with a
            # proxy or LB and those generally won't emit a JSON response) so throw it out a ServiceError so it can fall into
            # retry logic (depending on the error code)
            if response.ok:
                raise RuntimeError(error_text)
            else:
                raise oci.exceptions.ServiceError(
                    response.status_code,
                    response.reason,
                    response.headers,
                    error_text
                )

        if not response.ok:
            raise oci.exceptions.ServiceError(
                response.status_code,
                parsed_response.get('code'),
                response.headers,
                parsed_response.get('message')
            )
        else:
            if 'token' in parsed_response:
                self.security_token = SecurityTokenContainer(self.session_key_supplier, response.json()['token'])
            else:
                raise RuntimeError('Could not find token in response from auth service ({}): {}'.format(self.federation_endpoint, parsed_response))


class AuthTokenRequestSigner(oci.signer.AbstractBaseSigner):
    """
    A signer intended for X509FederationClient's use to request a token from Auth Service. Not intended for general use.
    """

    def __init__(self, tenancy_id, fingerprint, private_key_certificate_retriever):
        self.api_key = '{}/fed-x509/{}'.format(tenancy_id, fingerprint)
        self.private_key_certificate_retriever = private_key_certificate_retriever

        generic_headers = ["date", "(request-target)"]
        body_headers = ["content-length", "content-type", "x-content-sha256"]
        self.create_signers(self.api_key, self.private_key_certificate_retriever.get_private_key(), generic_headers, body_headers)
