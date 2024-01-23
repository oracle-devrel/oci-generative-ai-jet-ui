# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import struct
import json

from oci.encryption.internal.utils import (
    convert_to_bytes,
    convert_to_str,
    convert_bytes_to_base64_encoded_string,
    convert_base64_encoded_string_to_bytes,
)

from oci.encryption.internal.models import (
    EncryptedDataHeader,
    EncryptedDataHeaderDataEncryptionKey,
)

SERIALIZATION_FORMAT_VERSION = 0x0001

METADATA_KEY_ENCRYPTED_CONTENT_FORMAT = "encryptedContentFormat"
METADATA_KEY_ENCRYPTED_DATA_KEYS = "encryptedDataKeys"
METADATA_KEY_IV = "iv"
METADATA_KEY_ALGORITHM_ID = "algorithmId"
METADATA_KEY_ADDITIONAL_AUTHENTICATED_DATA = "additionalAuthenticatedData"

ENCRYPTED_DATA_KEY_MASTER_KEY_ID = "masterKeyId"
ENCRYPTED_DATA_KEY_VAULT_ID = "vaultId"
ENCRYPTED_DATA_KEY_ENCRYPTED_DATA_KEY = "encryptedDataKey"
ENCRYPTED_DATA_KEY_REGION = "region"

# docs: https://docs.python.org/3.8/library/struct.html
STRUCT_HEADER_FORMAT = (
    ">"  # big endian
    "H"  # serialization format version ID
    "I"  # JSON metadata length
    "{json_metadata_length}s"  # JSON metadata
)


def serialize_header(encrypted_data_header):
    encrypted_data_keys = []
    for encrypted_data_key in encrypted_data_header.encrypted_data_keys:
        encrypted_data_keys.append(
            {
                ENCRYPTED_DATA_KEY_MASTER_KEY_ID: encrypted_data_key.master_key_id,
                ENCRYPTED_DATA_KEY_VAULT_ID: encrypted_data_key.vault_id,
                ENCRYPTED_DATA_KEY_ENCRYPTED_DATA_KEY: convert_bytes_to_base64_encoded_string(
                    encrypted_data_key.encrypted_data_key_bytes
                ),
                ENCRYPTED_DATA_KEY_REGION: encrypted_data_key.region,
            }
        )

    metadata = {
        METADATA_KEY_ENCRYPTED_CONTENT_FORMAT: encrypted_data_header.encrypted_content_format,
        METADATA_KEY_ENCRYPTED_DATA_KEYS: encrypted_data_keys,
        METADATA_KEY_IV: convert_bytes_to_base64_encoded_string(
            encrypted_data_header.iv_bytes
        ),
        METADATA_KEY_ALGORITHM_ID: encrypted_data_header.algorithm_id,
        METADATA_KEY_ADDITIONAL_AUTHENTICATED_DATA: convert_to_str(
            encrypted_data_header.additional_authenticated_data_bytes
        ),
    }

    json_header_as_string = json.dumps(metadata)
    header_format = STRUCT_HEADER_FORMAT.format(
        json_metadata_length=len(json_header_as_string)
    )

    packed_header = struct.pack(
        header_format,
        SERIALIZATION_FORMAT_VERSION,
        len(json_header_as_string),
        convert_to_bytes(json_header_as_string),
    )

    return packed_header


def deserialize_header_from_stream(ciphertext_stream):
    short_format = ">H"
    short_size_offset = struct.calcsize(short_format)
    unsigned_int_format = ">I"
    unsigned_int_size_offset = struct.calcsize(unsigned_int_format)
    offset = 0

    # get serialization format version
    next_content = ciphertext_stream.read(short_size_offset)
    (serialization_format_version,) = struct.unpack_from(
        short_format, next_content, offset
    )
    offset = offset + short_size_offset

    if serialization_format_version != SERIALIZATION_FORMAT_VERSION:
        raise ValueError(
            "Could not deserialize header with unrecognized serialization format version: {}".format(
                serialization_format_version
            )
        )

    # get json metadata length
    next_content = ciphertext_stream.read(unsigned_int_size_offset)
    (json_metadata_length,) = struct.unpack_from(unsigned_int_format, next_content)
    offset = offset + short_size_offset

    # get json metadata
    chunk_format = "{}s".format(json_metadata_length)
    next_content = ciphertext_stream.read(struct.calcsize(chunk_format))
    (json_metadata_bytes,) = struct.unpack_from(chunk_format, next_content)
    offset = offset + struct.calcsize(chunk_format)

    json_metadata = convert_to_str(json_metadata_bytes)

    try:
        metadata = json.loads(json_metadata)
    except ValueError as e:
        raise ValueError(
            "Could not parse metadata inside header. Error: {}".format(str(e))
        )

    required_top_level_keys = [
        METADATA_KEY_IV,
        METADATA_KEY_ALGORITHM_ID,
        METADATA_KEY_ADDITIONAL_AUTHENTICATED_DATA,
    ]

    required_encrypted_data_key_keys = [
        ENCRYPTED_DATA_KEY_MASTER_KEY_ID,
        ENCRYPTED_DATA_KEY_VAULT_ID,
        ENCRYPTED_DATA_KEY_ENCRYPTED_DATA_KEY,
        ENCRYPTED_DATA_KEY_REGION,
    ]

    missing_or_none_top_level_keys = [required_key for required_key in required_top_level_keys if (required_key not in metadata) or (metadata.get(required_key, None) is None) or (isinstance(metadata.get(required_key), list) and len(metadata.get(required_key)) == 0)]
    if missing_or_none_top_level_keys:
        raise ValueError(
            "Invalid header. The following metadata keys must be present and not null: {}.".format(
                ", ".join(missing_or_none_top_level_keys)
            )
        )

    encrypted_data_keys_raw = metadata.get(METADATA_KEY_ENCRYPTED_DATA_KEYS)
    encrypted_data_keys = []
    for encrypted_data_key_raw in encrypted_data_keys_raw:
        missing_or_none_dek_keys = [required_key for required_key in required_encrypted_data_key_keys if (required_key not in encrypted_data_key_raw) or (encrypted_data_key_raw.get(required_key, None) is None)]
        if missing_or_none_dek_keys:
            raise ValueError(
                "Invalid header. The following metadata keys must be present and not null in each encrypted data key: {}.".format(
                    ", ".join(missing_or_none_dek_keys)
                )
            )

        encrypted_data_keys.append(
            EncryptedDataHeaderDataEncryptionKey(
                master_key_id=encrypted_data_key_raw.get(
                    ENCRYPTED_DATA_KEY_MASTER_KEY_ID
                ),
                vault_id=encrypted_data_key_raw.get(ENCRYPTED_DATA_KEY_VAULT_ID),
                encrypted_data_key_bytes=convert_base64_encoded_string_to_bytes(
                    encrypted_data_key_raw.get(ENCRYPTED_DATA_KEY_ENCRYPTED_DATA_KEY)
                ),
                region=encrypted_data_key_raw.get(ENCRYPTED_DATA_KEY_REGION),
            )
        )

    header = EncryptedDataHeader(
        encrypted_data_keys=encrypted_data_keys,
        iv_bytes=convert_base64_encoded_string_to_bytes(metadata.get(METADATA_KEY_IV)),
        algorithm_id=metadata.get(METADATA_KEY_ALGORITHM_ID),
        additional_authenticated_data_bytes=convert_to_bytes(
            metadata.get(METADATA_KEY_ADDITIONAL_AUTHENTICATED_DATA)
        ),
    )

    return header
