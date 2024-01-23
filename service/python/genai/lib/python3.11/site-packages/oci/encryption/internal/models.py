# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

ENCRYPTED_CONTENT_FORMAT_FULL_MESSAGE = 0


class EncryptedDataHeader(object):
    def __init__(
        self,
        encrypted_data_keys,
        iv_bytes,
        algorithm_id,
        additional_authenticated_data_bytes
    ):
        self.encrypted_content_format = ENCRYPTED_CONTENT_FORMAT_FULL_MESSAGE
        self.encrypted_data_keys = encrypted_data_keys
        self.iv_bytes = iv_bytes
        self.algorithm_id = algorithm_id
        self.additional_authenticated_data_bytes = additional_authenticated_data_bytes


class EncryptedDataHeaderDataEncryptionKey(object):
    def __init__(self, master_key_id, vault_id, encrypted_data_key_bytes, region):
        self.master_key_id = master_key_id
        self.vault_id = vault_id
        self.encrypted_data_key_bytes = encrypted_data_key_bytes
        self.region = region
