# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import oci.signer
from oci.exceptions import InvalidResourcePrincipalArguments, InvalidPrivateKey


class KeyPairSigner(oci.signer.AbstractBaseSigner):
    """
        A requests auth instance that is intended to be used when signing requests for RPv2.1 using a key pair
            - resource_id: The resource id of the Resource being used
            - private_key_content: The private key is provided directly in PEM format.
            - pass_phrase: The pass_phrase to be used for the private key (optional)
    """

    def __init__(self, rp_version, resource_id, tenancy_id, private_key_content, pass_phrase=None,
                 generic_headers=["date", "(request-target)", "host"],
                 body_headers=["content-length", "content-type", "x-content-sha256"]):
        if rp_version == "2.1.1" and tenancy_id and resource_id:
            self.api_key = "resource/v2.1.1/" + tenancy_id + "/" + resource_id
        elif rp_version == "2.1" and resource_id:
            self.api_key = "resource/v2.1/" + resource_id
        else:
            raise InvalidResourcePrincipalArguments("Resource Id or Tenancy Id or OCI_RESOURCE_PRINCIPAL_VERSION is missing")
        if private_key_content:
            self.private_key = oci.signer.load_private_key(private_key_content, pass_phrase)
        else:
            raise InvalidPrivateKey("Private Key is missing")

        self.generic_headers = generic_headers
        self.body_headers = body_headers
        self.create_signers(self.api_key, self.private_key, self.generic_headers, self.body_headers)
