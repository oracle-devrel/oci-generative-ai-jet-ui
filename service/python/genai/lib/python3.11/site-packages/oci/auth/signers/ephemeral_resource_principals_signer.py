# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import threading
import oci
import os
from .security_token_signer import SecurityTokenSigner, SECURITY_TOKEN_FORMAT_STRING
from ..security_token_container import SecurityTokenContainer

RP_DEBUG_INFORMATION_LOG = "Resource principals authentication can only be used in certain OCI services. Please check that the OCI service you're running this code from supports Resource principals. See https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdk_authentication_methods.htm#sdk_authentication_methods_resource_principal for more info."


class EphemeralResourcePrincipalSigner(SecurityTokenSigner):
    def __init__(self, session_token=None, private_key=None, private_key_passphrase=None, region=None, generic_headers=None, **kwargs):
        """
        This signer takes the following parameters:
        - session_token
        - private_key
        - private_key_passphrase

            These three parameters may be used in one of two modes. In the first mode, they contain the actual
            contents of the Resource Pricipals Session Token, private key (in PEM format) and the passphrase.
            This mode is only useful for short-lived programs.

            In the second mode, if these parameters contain absolute paths, then those paths are taken as the
            on-filesystem location of the values in question. The signer may attempt to reload these values from
            the filesystem on receiving a 401 response from an OCI service. This mode is used in cases where the
            program executes in an environment where an external provider may inject updated tokens into
            the filesystem.

        - region: the canonical region name

            This is utilised in locating the "local" endpoints of services.
        """
        # Setup for 2.2
        self._reset_signers_lock = threading.Lock()
        self.region = self._initialize_and_return_region(region)
        self._rpst = session_token
        if self._rpst is None:
            raise ValueError("session_token was not provided " + RP_DEBUG_INFORMATION_LOG)

        # Load the initial values
        self.session_key_supplier = self._construct_session_key_supplier(private_key, private_key_passphrase)
        self.security_token = SecurityTokenContainer(self.session_key_supplier,
                                                     self._get_resource_principal_session_token())

        # After load, the RPST holds claims for tenancy and compartment.
        self._reset_claims()

        # Get the Resource Principal Session Token and use it to set up the signer
        if generic_headers:
            super(EphemeralResourcePrincipalSigner, self).__init__(self.security_token.security_token,
                                                                   self.session_key_supplier.get_key_pair()['private'],
                                                                   generic_headers=generic_headers)
        else:
            super(EphemeralResourcePrincipalSigner, self).__init__(self.security_token.security_token,
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

    def _construct_session_key_supplier(self, private_key=None, private_key_passphrase=None):
        if private_key is None:
            raise ValueError("private_key must be provided " + RP_DEBUG_INFORMATION_LOG)
        passphrase = private_key_passphrase
        if os.path.isabs(private_key):
            return FileBasedSessionKeySupplier(private_key, passphrase)
        else:
            return FixedSessionKeySupplier(oci.signer.load_private_key(private_key, passphrase))

    def get_security_token(self):
        """
        Get the security token
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

            # Load RPST
            self.security_token = SecurityTokenContainer(self.session_key_supplier,
                                                         self._get_resource_principal_session_token())
            self._reset_signers()

            # Resources may be moved between compartments. Update any coordinates on refresh.
            self._reset_claims()
            return self.security_token.security_token
        finally:
            self._reset_signers_lock.release()

    def _get_resource_principal_session_token(self):
        """
        Get the Resource Principal Session Token
        """
        if os.path.isabs(self._rpst):
            with open(self._rpst) as f:
                return f.read()
        else:
            return self._rpst

    def _reset_signers(self):
        self.api_key = SECURITY_TOKEN_FORMAT_STRING.format(self.security_token.security_token)
        self.private_key = self.session_key_supplier.get_key_pair()['private']

        self._basic_signer.reset_signer(self.api_key, self.private_key)
        self._body_signer.reset_signer(self.api_key, self.private_key)

    def _reset_claims(self):
        self.tenancy_id = self.get_claim("res_tenant")
        self.compartment_id = self.get_claim("res_compartment")

    def get_claim(self, claim):
        """
        Provide access to the claims on the session token
        """
        return self.security_token.get_jwt().get(claim)


class FixedSessionKeySupplier(object):
    """FixedSessionKeySupplier holds a fixed session key that never updates"""
    def __init__(self, private_key=None):
        """
        A supplier that vends a single fixed private and public key.

        :param private_key:
            The private key to use.
        """
        self.private_key = private_key
        self.public_key = private_key.public_key()

    def get_key_pair(self):
        return {'private': self.private_key, 'public': self.public_key}

    def refresh(self):
        pass


class FileBasedSessionKeySupplier(object):
    """FileBasedSessionKeySupplier holds a private key that's loaded (and potentially refreshed) from a file source.

    :param private_key_file:
        The location to read the private key from

    :param passphrase_file (optional):
        The location to read the associated passphrase from
    """
    def __init__(self, private_key_file=None, passphrase_file=None):
        """
        A supplier that vends a private and public key loaded from a location on the filesystem

        :param private_key:
            The private key to use.
        """
        self.private_key_file = private_key_file
        self.passphrase_file = passphrase_file
        self.private_key = self.public_key = None
        self._refresh_lock = threading.Lock()

        self.refresh()

    def get_key_pair(self):
        return {'private': self.private_key, 'public': self.public_key}

    def refresh(self):
        pass_phrase = None
        if self.passphrase_file is not None:
            with open(self.passphrase_file, "b") as f:
                pass_phrase = f.read()
        self.private_key = oci.signer.load_private_key_from_file(self.private_key_file, pass_phrase)
        self.public_key = self.private_key.public_key()
