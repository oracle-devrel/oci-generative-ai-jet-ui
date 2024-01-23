# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from oci.encryption.encryption import (
    encrypt,
    decrypt,
    create_encryption_stream,
    create_decryption_stream,
)

from oci.encryption.key_providers import KMSMasterKeyProvider, KMSMasterKey, MasterKeyProvider, MasterKey
from oci.encryption.models import CryptoResult, CryptoResultStream


__all__ = (
    "encrypt",
    "decrypt",
    "create_encryption_stream",
    "create_decryption_stream",
    "KMSMasterKeyProvider",
    "KMSMasterKey",
    "MasterKeyProvider",
    "MasterKey",
    "CryptoResult",
    "CryptoResultStream"
)
