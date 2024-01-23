# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from oci._vendor import requests
from oci._vendor.requests.exceptions import HTTPError
from oci.exceptions import ServiceError

import oci.retry
import os.path
from oci._vendor import six
import threading
import logging
import pprint

# A retry strategy for use when calling the metadata endpoint on an instance to retrieve certificates. This retry strategy
# will retry on any exception (the metadata endpoint does not throw errors like an OCI service) up to 5 times or a max
# of 5 minutes
INSTANCE_METADATA_URL_CERTIFICATE_RETRIEVER_RETRY_STRATEGY = oci.retry.RetryStrategyBuilder().add_max_attempts() \
                                                                                             .add_total_elapsed_time() \
                                                                                             .get_retry_strategy()


# An abstract class which defines the interface via which certificates (and their corresponding private key) can be retrieved.
# Implementors should define their own concrete fetching mechanism (e.g. a URL, from a file, from provided PEM-format strings)
# but they are expected to be able to vend information in various ways:
#
#   - A dictionary containing all certificate and private key information. This is defined as:
#       - certificate: the certificate PEM string
#       - private_key_pem: the private key PEM string
#       - private_key: the private key as a cryptography.io X509 certificate object
#   - The certificate as a cryptography.io X509 certificate object
#   - The certificate PEM string
#   - The private key PEM string
#   - The private key as a cryptography.io X509 certificate object
#
# Certificates are optionally refreshable via a refresh() method. Where the refresh may not make sense (e.g. if the PEM-format strings
# are provided directly), implementors should make refersh() a no-op rather than throwing an exception.
class AbstractCertificateRetriever(object):
    def __init__(self, **kwargs):
        self.certificate_and_private_key = {
            'certificate': None,
            'private_key_pem': None,
            'private_key': None
        }

    # Refreshes the certificates held by this object (e.g. because they have been rotated)
    def refresh(self):
        raise NotImplementedError('Subclasses should implement this')

    # Returns the certificate_and_private_key dictionary contained by this object
    def get_certificate_and_private_key(self):
        raise NotImplementedError('Subclasses should implement this')

    # Retrieves the certificate as a cryptography.x509.Certificate
    def get_certificate_as_certificate(self):
        raise NotImplementedError('Subclasses should implement this')

    # Retrieves a string containing the certificate contents
    def get_certificate_raw(self):
        raise NotImplementedError('Subclasses should implement this')

    # Retrievea a string containing the PEM-encoded private key
    def get_private_key_pem(self):
        raise NotImplementedError('Subclasses should implement this')

    # Retrieves the private key as a cryptography private key
    def get_private_key(self):
        raise NotImplementedError('Subclasses should implement this')


class UrlBasedCertificateRetriever(AbstractCertificateRetriever):
    """
    A certificate retriever which reads PEM-format strings from URLs.

    :param str certificate_url:
        The URL from which to retrieve a certificate. It is assumed that what we retrieve is the PEM-formatted string for the certificate.
        This is mandatory

    :param str private_key_url: (optional)
        The URL from which to retrieve the private key corresponding to certificate_url (if any). It is assumed that what we retrieve is the PEM-formatted string for
        the private key.

    :param str passphrase: (optional)
        The passphrase of the private key (if any).

    :param obj retry_strategy: (optional)
        A retry strategy to use when retrieving the certificate and private key from the URLs provided to this class. This should be one of the strategies available in
        the :py:mod:`~oci.retry` module. By default this retriever will not perform any retries.

    :param bool log_requests: (optional)
        log_request if set to True will log the request url and response data when retrieving
        the certificate & corresponding private key (if there is one defined for this retriever)

    **Note:** This class is used internally, it is not recommended for user's direct use.
    """

    READ_CHUNK_BYTES = 1024 * 1024  # A mebibyte

    def __init__(self, **kwargs):
        super(UrlBasedCertificateRetriever, self).__init__()

        if 'certificate_url' not in kwargs:
            raise TypeError('certificate_url must be supplied as a keyword argument')

        self.cert_url = kwargs['certificate_url']
        self.private_key_url = kwargs.get('private_key_url')
        self.passphrase = kwargs.get('passphrase')
        self.retry_strategy = kwargs.get('retry_strategy')

        self.logger = logging.getLogger("{}.{}".format(__name__, id(self)))
        self.logger.addHandler(logging.NullHandler())

        if kwargs.get('log_requests'):
            self.logger.disabled = False
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.disabled = True

        if self.passphrase and isinstance(self.passphrase, six.text_type):
            self.passphrase = self.passphrase.encode('ascii')

        self._refresh_lock = threading.Lock()
        self.requests_session = requests.Session()
        if kwargs.get('headers', None):
            self.requests_session.headers.update(kwargs.get('headers'))

        self.refresh()

    def refresh(self):
        """
        Refresh the token by making a call to Identity for a new token.
        Returns the new token.
        """
        self._refresh_lock.acquire()
        try:
            if self.retry_strategy:
                self.retry_strategy.make_retrying_call(self._refresh_inner)
            else:
                self._refresh_inner()
        finally:
            self._refresh_lock.release()

    def get_certificate_and_private_key(self):
        """
        Returns the certificate_and_private_key dictionary contained by this object
        """
        self._refresh_lock.acquire()
        ret_val = self.certificate_and_private_key.copy()
        self._refresh_lock.release()

        return ret_val

    def get_certificate_as_certificate(self):
        """
        Retrieves the certificate as a cryptography.x509.Certificate
        """
        raw_cert = self.get_certificate_raw()
        if raw_cert:
            return x509.load_pem_x509_certificate(raw_cert, default_backend())
        else:
            return None

    def get_certificate_raw(self):
        """
        Retrieves a string containing the certificate contents
        """
        self._refresh_lock.acquire()
        certificate = self.certificate_and_private_key.copy()['certificate']
        self._refresh_lock.release()

        return certificate

    def get_private_key_pem(self):
        """
        Retrievea a string containing the PEM-encoded private key
        """
        self._refresh_lock.acquire()
        private_key = self.certificate_and_private_key.copy()['private_key_pem']
        self._refresh_lock.release()

        return private_key

    def get_private_key(self):
        """
        Retrieves the private key as a cryptography private key
        """
        self._refresh_lock.acquire()
        private_key = self.certificate_and_private_key.copy()['private_key']
        self._refresh_lock.release()

        return private_key

    def _refresh_inner(self):
        """
        Refreshes the certificate and its corresponding private key (if there is one defined for this retriever).
        This method represents the unit of retrying for the certificate retriever. It is intentionally coarse
        grained (e.g. if we retrieve the certificate but fail to retrieve the private key then we'll retry and
        retrieve both the certificate and private key again) to try and best maintain consistency in the data.

        For example, if we had separate retries for the certificate and the private key, in the scenario where
        a certificate was successfully retrieved but the private key failed, the private key we successfully
        retrieved upon retry may not relate to the certificate that we retrieved (e.g. because of rotation). This
        is still a risk in coarse grained retries, but hopefully a smaller one.
        """
        import oci.signer

        downloaded_certificate = six.BytesIO()
        self.logger.debug("Requesting certificate from : %s " % (self.cert_url))
        response = self.requests_session.get(self.cert_url, stream=True, timeout=(10, 60))
        self.logger.debug("Receiving certificate response......\n{}\n".format(pprint.pformat(
            {"status_code": response.status_code, "url": response.url, "header": dict(response.headers.items()),
                "reason": response.reason}, indent=2)))

        try:
            response.raise_for_status()
        except HTTPError as e:
            raise ServiceError(e.response.status_code, e.errno, e.response.headers, str(e))

        for chunk in response.raw.stream(self.READ_CHUNK_BYTES, decode_content=False):
            downloaded_certificate.write(chunk)

        self.certificate_and_private_key['certificate'] = downloaded_certificate.getvalue().strip()
        downloaded_certificate.close()
        if isinstance(self.certificate_and_private_key['certificate'], six.text_type):
            self.certificate_and_private_key['certificate'] = self.certificate_and_private_key['certificate'].encode('ascii')

        self._check_valid_certificate_string(self.certificate_and_private_key['certificate'])

        if self.private_key_url:
            downloaded_private_key_raw = six.BytesIO()
            self.logger.debug("Requesting private key from : %s " % (self.private_key_url))
            response = self.requests_session.get(self.private_key_url, stream=True, timeout=(10, 60))

            self.logger.debug("Receiving private key response......\n{}\n".format(pprint.pformat(
                {"status_code": response.status_code, "url": response.url, "header": dict(response.headers.items()),
                    "reason": response.reason}, indent=2)))

            try:
                response.raise_for_status()
            except HTTPError as e:
                raise ServiceError(e.response.status_code, e.errno, e.response.headers, str(e))

            for chunk in response.raw.stream(self.READ_CHUNK_BYTES, decode_content=False):
                downloaded_private_key_raw.write(chunk)

            self.certificate_and_private_key['private_key_pem'] = downloaded_private_key_raw.getvalue().strip()
            downloaded_private_key_raw.close()

            if isinstance(self.certificate_and_private_key['private_key_pem'], six.text_type):
                self.certificate_and_private_key['private_key_pem'] = self.certificate_and_private_key['private_key_pem'].encode('ascii')

            try:
                self.certificate_and_private_key['private_key'] = oci.signer.load_private_key(
                    self.certificate_and_private_key['private_key_pem'],
                    self.passphrase
                )
            except oci.exceptions.InvalidPrivateKey:
                raise InvalidCertificateFromInstanceMetadataError(
                    certificate_type='private_key',
                    certificate_raw=self.certificate_and_private_key['private_key_pem']
                )

    def _check_valid_certificate_string(self, certificate_string_to_check):
        """
        Determines whether a given string is a valid certificate. Valid in this context means that it
        can be parsed into a cryptography.io X509 certificate object. If the string is not valid then
        this method will throw an exception.

        :param str certificate_string_to_check:
            The certificate string to check. If it is valid then it should be a PEM-formatted string
            and able to be parsed into a cryptography.io X509 certificate object
        """
        try:
            x509.load_pem_x509_certificate(certificate_string_to_check, default_backend())
        except ValueError:
            raise InvalidCertificateFromInstanceMetadataError(
                certificate_type='certificate',
                certificate_raw=certificate_string_to_check
            )


class PEMStringCertificateRetriever(AbstractCertificateRetriever):
    """
    A certificate retriever which is provided PEM format strings directly. This retriever is non-refreshable, and calling refresh() is a no-op.

    :param str certificate_pem:
        The PEM-formatted string of the certificate. This is mandatory.

    :param str private_key_pem (optional):
        The PEM-formatted string of the private key corresponding to certificate_pem (if any).

    :param str passphrase (optional):
        The passphrase of the private key (if any).

    **Note:** This class is used internally, it is not recommended for user's direct use.
    """

    def __init__(self, **kwargs):
        import oci.signer

        super(PEMStringCertificateRetriever, self).__init__()

        if 'certificate_pem' not in kwargs:
            raise TypeError('certificate_pem must be supplied as a keyword argument')

        if isinstance(kwargs['certificate_pem'], six.text_type):
            self.certificate_and_private_key['certificate'] = kwargs['certificate_pem'].encode('ascii')
        else:
            self.certificate_and_private_key['certificate'] = kwargs['certificate_pem']

        if 'private_key_pem' in kwargs and kwargs['private_key_pem']:
            if isinstance(kwargs['private_key_pem'], six.text_type):
                self.certificate_and_private_key['private_key_pem'] = kwargs['private_key_pem'].encode('ascii')
            else:
                self.certificate_and_private_key['private_key_pem'] = kwargs['private_key_pem']

            if 'passphrase' in kwargs and kwargs['passphrase']:
                passphrase = kwargs['passphrase'].encode('ascii')
            else:
                passphrase = None

            self.certificate_and_private_key['private_key'] = oci.signer.load_private_key(
                self.certificate_and_private_key['private_key_pem'],
                passphrase
            )

    def refresh(self):
        """
        Since these are just the string, there is no refresh as such. A new object should be created
        if the strings change
        """
        pass

    def get_certificate_and_private_key(self):
        """
        Returns the certificate_and_private_key dictionary contained by this object
        """
        return self.certificate_and_private_key.copy()

    def get_certificate_as_certificate(self):
        """
        Retrieves the certificate as a cryptography.x509.Certificate
        """
        return x509.load_pem_x509_certificate(self.certificate_and_private_key['certificate'], default_backend())

    def get_certificate_raw(self):
        """
        Retrieves a string containing the certificate contents
        """
        return self.certificate_and_private_key['certificate']

    def get_private_key_pem(self):
        """
        Retrieve a a string containing the PEM-encoded private key
        """
        return self.certificate_and_private_key['private_key_pem']

    def get_private_key(self):
        """
        Retrieves the private key as a cryptography private key
        """
        return self.certificate_and_private_key['private_key']


class FileBasedCertificateRetriever(PEMStringCertificateRetriever):
    """
    A specialization of PEMStringCertificateRetriever which reads certificates from a file. This retriever is non-refreshable, and calling refresh() is a no-op.

    :param str certificate_file_path:
        The file path from which to retrieve a certificate. It is assumed that what we retrieve is the PEM-formatted string for the certificate.
        This is mandatory

    :param str private_key_pem_file_path (optional):
        The file path from which to retrieve the private key corresponding to certificate_file_path (if any). It is assumed that what we retrieve is the PEM-formatted string for
        the private key.

    :param str passphrase (optional):
        The passphrase of the private key (if any).

    **Note:** This class is used internally, it is not recommended for user's direct use.
    """

    def __init__(self, **kwargs):
        if 'certificate_file_path' not in kwargs:
            raise TypeError('certificate_file_path must be supplied as a keyword argument')

        if 'private_key_pem_file_path' in kwargs:
            private_key_pem = self._load_data_from_file(kwargs['private_key_pem_file_path'])
        else:
            private_key_pem = None

        parent_class_kwargs = {
            'certificate_pem': self._load_data_from_file(kwargs['certificate_file_path']),
            'private_key_pem': private_key_pem,
            'passphrase': kwargs.get('passphrase')
        }

        super(FileBasedCertificateRetriever, self).__init__(**parent_class_kwargs)

    def _load_data_from_file(self, filename):
        filename = os.path.expanduser(filename)
        with open(filename, mode="rb") as f:
            cert_data = f.read().strip()

        return cert_data


class InvalidCertificateFromInstanceMetadataError(Exception):
    def __init__(self, certificate_type='certificate', certificate_raw=None):
        self.certificate_raw = certificate_raw
        self.certificate_type = certificate_type
        super(InvalidCertificateFromInstanceMetadataError, self).__init__({
            'message': 'Invalid certificate returned from instance metadata. Expected a PEM-formatted string',
            'certificate_type': self.certificate_type,
            'certificate_raw': self.certificate_raw
        })
