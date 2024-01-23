# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from oci._vendor import six
import abc


class CryptoResult(object):
    """
    The result of an SDK encryption or decryption operation.
    """
    def __init__(self, data, encryption_context):
        """
        Creates a CryptoResult object.

        :param bytes data:
            The encrypted or decrypted bytes associated with this CryptoResult.

        :param dict encryption_context:
            The encryption_context associated with this CryptoResult.
        """
        self._data = data
        self._encryption_context = encryption_context

    def get_data(self):
        """
        Returns the encrypted or decrypted bytes associated with this CryptoResult.

        :rtype: bytes
        """
        return self._data

    def get_encryption_context(self):
        """
        Returns the encryption context associated with this CryptoResult.

        Note that the SDK may internally add keys to the encryption context so the context returned
        is guaranteed to be a superset of the context passed in but not an exact match.

        :rtype: dict
        """
        return self._encryption_context


@six.add_metaclass(abc.ABCMeta)
class CryptoResultStream(object):
    """
    The result of an SDK stream encryption or decryption operation.
    """
    @abc.abstractmethod
    def read(self, size):
        """
        Read up to size bytes from the resulting encrypted or decrypted data and return them.

        :rtype: bytes
        """
        pass

    @abc.abstractmethod
    def close(self):
        """
        Close this CryptoResultStream and release the internal buffer.

        Once the CryptoResultStream is closed, any operation on the stream (e.g. reading) will raise a ValueError.

        As a convenience, it is allowed to call this method more than once; only the first call, however, will have an effect.

        Note: this does not close the underlying stream that the caller passed in during initialization.

        :rtype: None
        """
        pass

    @abc.abstractmethod
    def get_encryption_context(self):
        """
        Returns the encryption context associated with the stream being encrypted or decrypted.

        Note that the SDK may internally add keys to the encryption context so the context returned
        is guaranteed to be a superset of the context passed in but not an exact match.

        :rtype: dict
        """
        pass
