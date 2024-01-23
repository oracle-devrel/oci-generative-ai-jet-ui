# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import absolute_import

import base64
import email.utils
import hashlib
import io
import functools
import os

from oci._vendor import six
from oci.util import record_body_position_for_rewind, rewind_body, back_up_body_calculate_stream_content_length, read_stream_for_signing

from ._vendor import httpsig_cffi, requests
from .exceptions import InvalidPrivateKey, MissingPrivateKeyPassphrase

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import logging

logger = logging.getLogger(__name__)
SIGNATURE_VERSION = "1"


def load_private_key_from_file(filename, pass_phrase=None):
    filename = os.path.expanduser(filename)
    with io.open(filename, mode="rb") as f:
        private_key_data = f.read().strip()
    return load_private_key(private_key_data, pass_phrase)


def load_private_key(secret, pass_phrase):
    """Loads a private key that may use a pass_phrase.

    Tries to correct or diagnose common errors:

    - provided pass_phrase but didn't need one
    - provided a public key
    """
    if isinstance(secret, six.text_type):
        secret = secret.encode("ascii")
    if isinstance(pass_phrase, six.text_type):
        pass_phrase = pass_phrase.encode("ascii")

    backend = default_backend()

    try:
        # 0) Try with pass_phrase
        return serialization.load_pem_private_key(secret, pass_phrase, backend=backend)
    except TypeError:
        # 1) Either:
        #    - key has pass_phrase and one wasn't provided
        #    - key doesn't have pass_phrase and one was provided.
        #
        #    Can't fix the first, but we *can* fix the second.
        #    This can happen if the DEFAULT profile has a pass_phrase but
        #    another profile uses a key file without a pass_phrase.
        if pass_phrase is None:
            # 1.1) private key needed a pass_phrase and we don't have one
            raise MissingPrivateKeyPassphrase("The provided key requires a passphrase.")
        else:
            # 1.2) try again without pass_phrase; could be an artifact from DEFAULT
            return serialization.load_pem_private_key(secret, None, backend=backend)
    except ValueError:
        # 2) Try to determine what kind of failure this is.
        #    Most likely, this is either a bad password or a public key.
        #    If loading it as a public key fails, it's almost certainly a bad password.
        for loader in [
            serialization.load_der_public_key,
            serialization.load_pem_public_key,
            serialization.load_ssh_public_key
        ]:
            try:
                loader(secret, backend=backend)
            except (ValueError, UnsupportedAlgorithm):
                # 2.1) Not a public key; try the next format
                pass
            else:
                # 2.2) This is a public key
                raise InvalidPrivateKey("Authentication requires a private key, but a public key was provided.")
        # 2.3) Password is probably wrong.
        raise InvalidPrivateKey("The provided key is not a private key, or the provided passphrase is incorrect.")


def inject_missing_headers(request, sign_body, enforce_content_headers):
    # Inject date, host, and content-type if missing
    request.headers.setdefault(
        "date", email.utils.formatdate(usegmt=True))

    request.headers.setdefault(
        "host", six.moves.urllib.parse.urlparse(request.url).netloc)

    if hasattr(request.body, "buffer") or hasattr(request.body, "read"):
        request.headers.setdefault("content-type", "application/octet-stream")
    request.headers.setdefault("content-type", "application/json")

    if enforce_content_headers:
        # Requests with a body need to send content-type,
        # content-length, and x-content-sha256
        if "x-content-sha256" not in request.headers and sign_body:
            body = request.body or ""
            m = hashlib.sha256()
            # Handle String types
            if isinstance(body, six.string_types):
                body = body.encode("utf-8")
                request.headers.setdefault("content-length", str(len(body)))
                m.update(body)
            # Handle bytes
            elif isinstance(body, (bytes, bytearray)):
                m.update(body)
            # Handling signing for Files/stdin
            elif hasattr(body, "buffer") or hasattr(body, "read"):
                is_body_rewindable, original_position = record_body_position_for_rewind(body)
                if is_body_rewindable:
                    content_length = read_stream_for_signing(m, body)
                    if content_length == -1:
                        raise IOError("Unable to read stream for signing! Please sign the stream yourself by using the custom header x-content-sha256")
                    request.headers.setdefault("content-length", str(content_length))
                    is_rewind_success = rewind_body(body, original_position)
                    if not is_rewind_success:
                        raise IOError("Unable to rewind request body while signing!")
                else:
                    logger.warning("Stream cannot be rewound, trying to backup and sign the body!")
                    stream = back_up_body_calculate_stream_content_length(body)
                    # Updating request body as it cannot be rewound
                    request.body = stream.get("byte_content")
                    m.update(stream.get("byte_content"))
                    request.headers.setdefault("content-length", str(stream.get("content_length")))
            # Update sha256 header
            if m:
                base64digest = base64.b64encode(m.digest())
                base64string = base64digest.decode("utf-8")
                request.headers["x-content-sha256"] = base64string


# HeaderSigner doesn't support private keys with passwords.
# Patched since the constructor parses the key in __init__
class _PatchedHeaderSigner(httpsig_cffi.sign.HeaderSigner):
    HEADER_SIGNER_TEMPLATE = 'Signature algorithm="rsa-sha256",headers="{}",keyId="{}",signature="%s",version="{}"'

    """Internal.  If you need to construct a Signer, use :class:`~.Signer` instead."""
    def __init__(self, key_id, private_key, headers):
        # Dropped general support for the specific signing/hash the SDK uses.
        self.sign_algorithm = "rsa"
        self.hash_algorithm = "sha256"

        self._hash = None
        self._rsahash = httpsig_cffi.utils.HASHES[self.hash_algorithm]

        self._rsa_private = private_key
        self._rsa_public = self._rsa_private.public_key()

        self.headers = headers
        self.signature_template = self.HEADER_SIGNER_TEMPLATE.format(" ".join(headers), key_id, SIGNATURE_VERSION)

    def reset_signer(self, key_id, private_key):
        self._hash = None
        self._rsa_private = private_key
        self._rsa_public = self._rsa_private.public_key()
        self.signature_template = self.HEADER_SIGNER_TEMPLATE.format(" ".join(self.headers), key_id, SIGNATURE_VERSION)


# An abstract class whose subclasses can sign requests. This contains the core logic for creating a signer and signing
# requests, but does not source the required information:
#
#   - api key
#   - private key
#   - headers
#
# As concrete implementations are expected to provide these and have their ways of sourcing/constructing them.
class AbstractBaseSigner(requests.auth.AuthBase):
    def create_signers(self, api_key, private_key, generic_headers, body_headers):
        self._basic_signer = _PatchedHeaderSigner(
            key_id=api_key,
            private_key=private_key,
            headers=generic_headers)

        self._body_signer = _PatchedHeaderSigner(
            key_id=api_key,
            private_key=private_key,
            headers=generic_headers + body_headers)

    def validate_request(self, request):
        verb = request.method.lower()
        if verb not in ["get", "head", "delete", "put", "post", "patch"]:
            raise ValueError("Don't know how to sign request verb {}".format(verb))

    def do_request_sign(self, request, enforce_content_headers=True):
        verb = request.method.lower()
        sign_body = verb in ["put", "post", "patch"]
        if sign_body and enforce_content_headers:
            signer = self._body_signer
        else:
            signer = self._basic_signer
            # The requests library sets the Transfer-Encoding header to 'chunked' if the
            # body is a stream with 0 length. Object storage does not currently support this option,
            # and the request will fail if it is not removed. This is the only hook available where we
            # can do this after the header is added and before the request is sent.
            request.headers.pop('Transfer-Encoding', None)

        inject_missing_headers(request, sign_body, enforce_content_headers)
        signed_headers = signer.sign(
            request.headers,
            host=six.moves.urllib.parse.urlparse(request.url).netloc,
            method=request.method,
            path=request.path_url)
        request.headers.update(signed_headers)

        return request

    def __call__(self, request, enforce_content_headers=True):
        self.validate_request(request)
        return self.do_request_sign(request, enforce_content_headers)

    @property
    def without_content_headers(self):
        return functools.partial(self, enforce_content_headers=False)


class Signer(AbstractBaseSigner):
    """
    A requests auth instance that can be reused across requests. This signer is intended to be used
    when signing requests for a given user and it requires that user's ID, their private key
    and cerificate fingerprint.

    The private key can be sourced from a file (private_key_file_location) or the PEM string can be
    provided directly (private_key_content).

    The headers to be signed by this signer are not customizable.

    You can manually sign calls by creating an instance of the signer, and
    providing it as the ``auth`` argument to Requests functions:

    .. code-block:: python

        import requests
        from oci import Signer

        auth = Signer(...)
        resp = requests.get("https://...", auth=auth)


    """

    def __init__(self, tenancy, user, fingerprint, private_key_file_location, pass_phrase=None, private_key_content=None):
        self.api_key = tenancy + "/" + user + "/" + fingerprint

        if private_key_content:
            self.private_key = load_private_key(private_key_content, pass_phrase)
        else:
            self.private_key = load_private_key_from_file(private_key_file_location, pass_phrase)

        generic_headers = ["date", "(request-target)", "host"]
        body_headers = ["content-length", "content-type", "x-content-sha256"]
        self.create_signers(self.api_key, self.private_key, generic_headers, body_headers)

    @staticmethod
    def from_config(config):
        from .config import validate_config
        validate_config(config)
        return Signer(
            config['tenancy'],
            config['user'],
            config['fingerprint'],
            private_key_file_location=config['key_file'],
            pass_phrase=config.get('pass_phrase'),
            private_key_content=config.get('key_content')
        )
