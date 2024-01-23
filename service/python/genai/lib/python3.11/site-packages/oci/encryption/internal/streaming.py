# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import os
import base64
import math
import json
from oci._vendor import six
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from threading import Lock

from oci.encryption.internal.serialization import (
    serialize_header,
    deserialize_header_from_stream,
)

from oci.encryption.internal.models import (
    EncryptedDataHeader,
    EncryptedDataHeaderDataEncryptionKey,
)

from oci.encryption.internal.defaults import DEFAULT_MAX_GCM_ENCRYPTION_SIZE, DEFAULT_ALGORITHM, DEFAULT_MAX_ENCRYPTION_SIZE_SENTINEL
from oci.encryption.internal.utils import (
    convert_to_bytes,
    convert_to_str,
    generate_random_iv,
    convert_encryption_context_to_string,
)

from oci.encryption.algorithms import Algorithm
from oci.encryption.models import CryptoResultStream


MAX_32_BIT_SIGNED_INTEGER = int(math.pow(2, 31) - 1)
MAX_ENCRYPTOR_DECRYPTOR_UPDATE_CHUNK_SIZE_IN_BYTES = MAX_32_BIT_SIGNED_INTEGER


def _update_cryptor_with_data(cryptor, data):
    result = b""
    if len(data) > MAX_ENCRYPTOR_DECRYPTOR_UPDATE_CHUNK_SIZE_IN_BYTES:
        start_index = 0
        memview = memoryview(data)
        while True:
            end_index = start_index + MAX_ENCRYPTOR_DECRYPTOR_UPDATE_CHUNK_SIZE_IN_BYTES
            next_data = memview[start_index:end_index]
            if len(next_data) == 0:
                break

            result += cryptor.update(data=next_data)

            start_index = end_index
    else:
        result = cryptor.update(data=data)

    return result


def _validate_encryption_context(encryption_context):
    if encryption_context is None:
        return

    if not isinstance(encryption_context, dict):
        raise TypeError("encryption_context must be a dict")

    invalid_keys = []
    invalid_values = []
    invalid_prefix_keys = []
    for key, value in six.iteritems(encryption_context):
        # keys and values must be str and not bytes
        # in python 2 'bytes' is just an alias for 'str' so it is okay
        if (str != bytes and isinstance(key, bytes)) or not isinstance(key, six.string_types):
            invalid_keys.append(key)
        elif key.startswith("oci-"):
            invalid_prefix_keys.append(key)

        if (str != bytes and isinstance(value, bytes)) or not isinstance(value, six.string_types):
            invalid_values.append(value)

    if invalid_keys or invalid_values:
        raise TypeError(
            "encryption_context must be a dict with string keys and string values. Invalid keys: {}. Invalid values: {}".format(
                str(invalid_keys), str(invalid_values)
            )
        )

    if invalid_prefix_keys:
        raise ValueError(
            "encryption_context cannot contain keys with prefix 'oci-'. Invalid keys: {}".format(
                str(invalid_prefix_keys),
            )
        )

    try:
        json.dumps(encryption_context)
    except ValueError as e:
        raise ValueError(
            "encryption_context must be JSON serializable. Error: {}".format(str(e))
        )


class StreamEncryptor(CryptoResultStream):
    def __init__(
        self,
        master_key_provider,
        stream_to_encrypt,
        max_encryption_size=DEFAULT_MAX_ENCRYPTION_SIZE_SENTINEL,
        encryption_context=None
    ):
        """
        Provides a stream that wraps 'stream_to_encrypt' and allows reading data from the underlying stream
        encrypted under the provided master key.

        :param int max_encryption_size: (optional)
            Max number of bytes able to be encrypted by this StreamEncryptor. The default value differs
            based on the algorithm used. For GCM (the default algorithm) the default value is 2147483647 bytes.
            This is provided mainly for use with authenticated encryption algorithms that require verification
            of an authentication tag upon decryption. Because decrypting using these algorithms will buffer
            the entire payload into memory before returning it, this max_encryption_size provides a sanity
            check against encrypting payloads too large to decrypt. This is possible because encryption does not
            require holding the entire payload in memory.

            The 2147483647 byte limit was chosen because that is the maximum number of bytes that can be encrypted or
            decrypted by the OCI Java SDK.  This is to avoid users accidentally encrypting payloads in Python that
            cannot be decrypted in Java.

            Explicitly passing this value as None will disable the size check and allow encrypting payloads up to
            the maximum size supported by the algorithm.

        :param dict encryption_context: (optional)
            Optional additional data to be provided as input to authenticated encryption
            algorithms. This must be a dict with keys that are strings and values that are strings. Keys may NOT
            match the prefix oci-* as that namespace is reserved for OCI internal keys that may be added to the AAD.
        """
        self._algorithm = DEFAULT_ALGORITHM
        self._primary_master_key = master_key_provider.get_primary_master_key()
        if not self._primary_master_key:
            raise ValueError("master_key_provider must contain a primary master key in order to encrypt data")

        self._data_encryption_key = self._primary_master_key.generate_data_encryption_key(
            self._algorithm
        )
        self._stream_to_encrypt = stream_to_encrypt

        _validate_encryption_context(encryption_context)
        self._encryption_context = encryption_context
        self._encryption_context_bytes = convert_to_bytes(
            convert_encryption_context_to_string(encryption_context)
        )

        self.iv = generate_random_iv(self._algorithm.iv_len)
        cipher = Cipher(
            algorithm=self._algorithm.algorithm(
                self._data_encryption_key.plaintext_key_bytes
            ),
            mode=self._algorithm.mode(self.iv),
            backend=default_backend(),
        )

        # use encryptor directly instead of AESGCM class
        # https://cryptography.io/en/latest/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM
        # so that we can optionally stream data during encryption without holding the entire payload in memory
        self.encryptor = cipher.encryptor()

        self._max_encryption_size = None
        if max_encryption_size is DEFAULT_MAX_ENCRYPTION_SIZE_SENTINEL:
            if self._algorithm.mode.name == modes.GCM.name:
                self._max_encryption_size = DEFAULT_MAX_GCM_ENCRYPTION_SIZE
            else:
                raise ValueError("Unrecognized algorithm provided: {}".format(str(self._algorithm)))
        elif max_encryption_size is not None:
            if not isinstance(max_encryption_size, int):
                raise TypeError("argument max_encryption_size must be an integer")

            self._max_encryption_size = max_encryption_size

        self._header_content = None
        self._buffer = b""
        self._bytes_written_total = 0
        self._bytes_written_excluding_header = 0
        self._finalized = False
        self._lock = Lock()
        self._closed = False

    def _build_header_content(self):
        # for right now there is only ever one encrypted data key
        encrypted_data_keys = [
            EncryptedDataHeaderDataEncryptionKey(
                master_key_id=self._primary_master_key.get_identifier(),
                vault_id=self._primary_master_key.vault_id,
                region=self._primary_master_key.region,
                encrypted_data_key_bytes=self._data_encryption_key.encrypted_key_bytes,
            )
        ]

        encrypted_data_header = EncryptedDataHeader(
            encrypted_data_keys=encrypted_data_keys,
            iv_bytes=self.iv,
            algorithm_id=self._algorithm.id,
            additional_authenticated_data_bytes=self._encryption_context_bytes,
        )

        return serialize_header(encrypted_data_header=encrypted_data_header)

    def _get_bytes_remaining_in_stream_to_encrypt_using_seek_and_tell(self):
        cur_pos = self._stream_to_encrypt.seek(0, os.SEEK_CUR)
        self._stream_to_encrypt.seek(0, os.SEEK_END)
        length = self._stream_to_encrypt.tell()
        self._stream_to_encrypt.seek(cur_pos)
        return length - cur_pos

    def _enforce_max_encryption_size(self, size_of_next_read):
        _total_bytes_requested_to_encrypt = (
            self._bytes_written_excluding_header + size_of_next_read
        )
        if size_of_next_read == -1:
            # we don't require input streams to be seekable
            # so we try to figure out preemptively if we are about to encrypt too much data
            # but if seeking is not allowed, we go ahead with the encryption and we always check
            # before returning any encrypted data that we haven't gone over _max_encryption_size
            if hasattr(self._stream_to_encrypt, "seek") and hasattr(self._stream_to_encrypt, "tell") and hasattr(self._stream_to_encrypt, "seekable") and self._stream_to_encrypt.seekable():
                _total_bytes_requested_to_encrypt = (
                    self._bytes_written_excluding_header + self._get_bytes_remaining_in_stream_to_encrypt_using_seek_and_tell()
                )

        if self._max_encryption_size is not None and (
            _total_bytes_requested_to_encrypt > self._max_encryption_size
        ):
            raise ValueError(
                "Attempted to encrypt > _max_encryption_size bytes. Total bytes requested to encrypt: {}. Max encryption size: {}.".format(
                    _total_bytes_requested_to_encrypt, self._max_encryption_size
                )
            )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        # do not allow one thread to close the stream while another
        # is actively reading
        self._lock.acquire()
        try:
            self._closed = True
            self._buffer = b""
        finally:
            self._lock.release()

    def get_encryption_context(self):
        return self._encryption_context

    def read(self, size=-1):
        """
        Read up to size bytes from the object and return them. As a convenience, if size is unspecified or -1,
        all bytes until EOF are returned.

        If 0 bytes are returned, and size was not 0, this indicates end of file.

        :param int size: (optional)
            The number of bytes to attempt to read from the underlying stream.

        :rtype: bytes
        """
        self._lock.acquire()
        try:
            if self._closed:
                raise ValueError("Cannot read from closed stream")

            if size == 0:
                return b""

            READ_ALL = size <= -1

            if not self._header_content:
                self._header_content = self._build_header_content()
                self._buffer += self._header_content

                if self._encryption_context_bytes:
                    self.encryptor.authenticate_additional_data(
                        self._encryption_context_bytes
                    )

            # try to throw early if this payload will exceed max encryption size
            self._enforce_max_encryption_size(size_of_next_read=size)

            # buffer doesn't have enough data to fulfill this read operation
            # so we need to load more info the buffer
            if not self._finalized and (size > len(self._buffer) or READ_ALL):
                if READ_ALL:
                    size_to_read_into_buffer = -1
                else:
                    size_to_read_into_buffer = size - len(self._buffer)

                reached_end = False

                # read 'size_to_read_into_buffer' bytes from underlying stream
                if READ_ALL:
                    bytes_to_encrypt = convert_to_bytes(
                        self._stream_to_encrypt.read()
                    )
                else:
                    bytes_to_encrypt = convert_to_bytes(
                        self._stream_to_encrypt.read(size_to_read_into_buffer)
                    )

                total_bytes_to_encrypt_size = len(bytes_to_encrypt)
                ciphertext = _update_cryptor_with_data(self.encryptor, bytes_to_encrypt)

                reached_end = (
                    total_bytes_to_encrypt_size < size_to_read_into_buffer
                ) or READ_ALL
                if reached_end:
                    ciphertext += self.encryptor.finalize() + self.encryptor.tag
                    self._finalized = True

                self._buffer += ciphertext

            # read output from buffer
            if READ_ALL:
                output = self._buffer[:]

                # remove the bytes that you just read from the buffer
                self._buffer = b""
            else:
                output = self._buffer[:size]

                # remove the bytes that you just read from the buffer
                self._buffer = self._buffer[size:]

            self._bytes_written_total += len(output)
            if self._bytes_written_total > len(self._header_content):
                self._bytes_written_excluding_header = self._bytes_written_total - len(
                    self._header_content
                )
            else:
                self._bytes_written_excluding_header = 0

            # we try to determine the payload size ahead of time and throw before wasting time encrypting
            # in some cases we can't determine the stream length ahead of time so we check again before
            # returning to make sure we haven't encrypted too much data
            self._enforce_max_encryption_size(size_of_next_read=0)

            return output
        finally:
            self._lock.release()


class StreamDecryptor(CryptoResultStream):
    def __init__(self, stream_to_decrypt, master_key_provider):
        """
        Returns a StreamDecryptor which produces decrypted data based on the underlying stream
        supplied as 'stream_to_decrypt'.

        :param oci.encryption.MasterKeyProvider master_key_provider: (required)
            A MasterKeyProvider to use for decrypting the data.

        :param stream stream_to_encrypt: (required)
            The stream to be decrypted.
        """
        self._stream_to_decrypt = stream_to_decrypt
        self._master_key_provider = master_key_provider

        # these can only be populated once the header is read
        self._decryptor = None
        self._algorithm = None

        self._buffer = b""
        self._header_deserialized = False
        self._finalized = False
        self._encryption_context = {}
        self._lock = Lock()
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        # do not allow one thread to close the stream while another
        # is actively reading
        self._lock.acquire()
        try:
            self._closed = True
            self._buffer = b""
        finally:
            self._lock.release()

    def _init_decryptor_and_header_related_fields(self, header):
        matching_algos = [algo for algo in Algorithm if header.algorithm_id == algo.id]
        if not matching_algos:
            raise ValueError(
                "Could not decrypt payload encrypted using unrecognized algorithm ID: {}".format(
                    header.algorithm_id
                )
            )
        else:
            self._algorithm = matching_algos[0]

        # the user passed in a key provider which is capable of vending master keys
        # we request the specific master key that can decrpt this payload
        encrypted_data_key = header.encrypted_data_keys[0]
        primary_master_key = self._master_key_provider.get_master_key(
            master_key_id=encrypted_data_key.master_key_id,
            vault_id=encrypted_data_key.vault_id,
            region=encrypted_data_key.region,
        )

        decrypted_dek_bytes = primary_master_key.decrypt(
            encrypted_data_key.encrypted_data_key_bytes
        )
        dek_plaintext_bytes = base64.b64decode(decrypted_dek_bytes)

        cipher = Cipher(
            algorithm=self._algorithm.algorithm(dek_plaintext_bytes),
            mode=self._algorithm.mode(header.iv_bytes),
            backend=default_backend(),
        )

        self._decryptor = cipher.decryptor()

        if len(header.additional_authenticated_data_bytes):
            self._encryption_context = json.loads(
                convert_to_str(header.additional_authenticated_data_bytes)
            )
            self._decryptor.authenticate_additional_data(
                header.additional_authenticated_data_bytes
            )

    def _handle_header(self):
        if not self._header_deserialized:
            # if the stream is closed we cannot attempt to read the header from the stream
            if self._closed:
                raise ValueError("Cannot read from closed stream")

            self._header_deserialized = True
            header = deserialize_header_from_stream(self._stream_to_decrypt)
            self._init_decryptor_and_header_related_fields(header)

    def get_encryption_context(self):
        self._lock.acquire()
        try:
            self._handle_header()
            return self._encryption_context
        finally:
            self._lock.release()

    def read(self, size=-1):
        """
        Read up to size bytes from the object and return them. As a convenience, if size is unspecified or -1,
        all bytes until EOF are returned.

        If 0 bytes are returned, and size was not 0, this indicates end of file.

        :param int size: (optional)
            The number of bytes to attempt to read from the underlying stream.

        :rtype: bytes
        """
        self._lock.acquire()
        try:
            if self._closed:
                raise ValueError("Cannot read from closed stream")

            if size == 0:
                return b""

            self._handle_header()

            # indicates whether to read and return all content from underlying stream + header + (optional) tag
            READ_ALL = size <= -1

            # we must read the entire ciphertext into memory to validate the tag before we
            # return any decrypted bytes
            # so if the buffer is not yet populated, read the entire stream into it
            if not self._finalized:
                self._finalized = True

                # read entire stream
                bytes_to_decrypt = convert_to_bytes(_read_full_stream_content(self._stream_to_decrypt))
                tag = bytes_to_decrypt[-self._algorithm.tag_len:]
                bytes_to_decrypt = bytes_to_decrypt[: -self._algorithm.tag_len]

                decrypted_data = _update_cryptor_with_data(
                    self._decryptor, bytes_to_decrypt
                )
                decrypted_data += self._decryptor.finalize_with_tag(tag)

                self._buffer += decrypted_data

            # read output from buffer
            if READ_ALL:
                output = self._buffer[:]

                # remove the bytes that you just read from the buffer
                self._buffer = b""
            else:
                output = self._buffer[:size]

                memview = memoryview(self._buffer)
                # remove the bytes that you just read from the buffer
                self._buffer = memview[size:]

            return output
        finally:
            self._lock.release()


def _read_full_stream_content(stream):
    if hasattr(stream, 'readall'):
        return convert_to_bytes(stream.readall)
    else:
        return convert_to_bytes(stream.read())
