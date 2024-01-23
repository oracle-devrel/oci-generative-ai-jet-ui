# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from oci._vendor import six
import os
from oci.encryption.internal.defaults import DEFAULT_ENCODING
import zlib
import base64
import json


def convert_to_bytes(data):
    if isinstance(data, six.string_types) and not isinstance(data, bytes):
        return data.encode(DEFAULT_ENCODING)
    return data


def convert_to_str(data):
    if isinstance(data, bytes):
        return data.decode(DEFAULT_ENCODING)
    return data


def convert_bytes_to_base64_encoded_string(data):
    if not isinstance(data, bytes):
        raise TypeError("Cannot convert non-bytes object")

    return convert_to_str(base64.b64encode(data))


def convert_base64_encoded_string_to_bytes(data):
    if not isinstance(data, six.string_types) or isinstance(data, bytes):
        raise TypeError("Cannot convert non string like object")

    return base64.b64decode(data)


def convert_encryption_context_to_string(encryption_context):
    # this includes transforming empty dict to ""
    if not encryption_context:
        return ""

    return json.dumps(encryption_context, sort_keys=True, separators=(",", ":"))


def generate_random_iv(iv_len):
    """Generates a random initialization vector (IV).

    :returns: Initialization vector
    :rtype: bytes
    """
    return os.urandom(iv_len)


def verify_crc32_checksum(input_bytes, checksum):
    # bitwise AND with all 1's is recommended by zlib.crc32 docs to ensure
    # the same output across all python versions and platforms
    # https://docs.python.org/2/library/zlib.html#zlib.crc32
    crc32_calculated_checksum = str(zlib.crc32(input_bytes) & 0xffffffff)
    if crc32_calculated_checksum != checksum:
        raise ValueError(
            "Could not verify integrity of data. Computed checksum: {}. Expected checksum: {}".format(
                crc32_calculated_checksum, checksum
            )
        )

    return True


def raise_runtime_error_from(runtime_exc_message, orig_exc):
    if six.PY2:
        # python 2 does not support exception chaining so we append the inner exception to the message
        raise RuntimeError("{} Caused by exception: {}".format(runtime_exc_message, str(orig_exc)))
    else:
        six.raise_from(RuntimeError(runtime_exc_message), orig_exc)
