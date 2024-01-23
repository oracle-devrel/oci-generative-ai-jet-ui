# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from cryptography.hazmat.primitives.ciphers import algorithms, modes

from enum import Enum


class Algorithm(Enum):
    """
    Represents an Algorithm that can be used to encrypt and decrypt payloads.
    """

    AES_256_GCM_IV12_TAG16 = (
        0,  # OCI SDK algo ID
        algorithms.AES,
        modes.GCM,
        32,  # key length
        12,  # initialization vector (IV) length, 96 bits is recommended, see section 5.2.1.1: https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf
        16,  # authentication tag length
        None,  # padding
        16,  # block size in bytes
    )

    def __init__(
        self,
        id,
        algorithm,
        mode,
        key_len,
        iv_len,
        tag_len=None,
        padding=None,
        block_size=None,
    ):
        """
        :param bytes id: (required)
            Identifier for this algorithm used in serialization

        :param cryptography.hazmat.primitives.ciphers.CipherAlgorithm algorithm: (required)
            Encryption algorithm to use.

        :param cryptography.hazmat.primitives.ciphers.modes.Mode mode: (required)
            Mode to use.

        :param int key_len: (required)
            Length of the key (in bytes).

        :param int iv_len: (required)
            Length of the initialization vector (in bytes).

        :param int tag_len: (optional)
            Length of the authentication tag (in bytes), if applicable.

        :param cryptography.hazmat.primitives.padding padding: (optional)
            Padding to use.

        :param int block_size: (optional)
            Size of each block.
        """
        self.id = id
        self.algorithm = algorithm
        self.mode = mode
        self.key_len = key_len
        self.iv_len = iv_len
        self.tag_len = tag_len
        self.padding = padding
        self.block_size = block_size
