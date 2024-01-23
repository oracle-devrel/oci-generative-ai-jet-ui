# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from oci._vendor import six

import abc
import base64
from cryptography.hazmat.primitives.ciphers import algorithms

from oci.exceptions import ServiceError
from oci.key_management.models import KeyShape, GenerateKeyDetails, DecryptDataDetails
from oci.key_management import KmsCryptoClient, KmsManagementClient, KmsVaultClient
from oci.encryption.internal.utils import (
    convert_to_str,
    verify_crc32_checksum,
    raise_runtime_error_from
)


@six.add_metaclass(abc.ABCMeta)
class MasterKeyProvider(object):
    """
    An abstract base class defining methods to vend MasterKeys
    for use in encryption and decryption.
    """
    @abc.abstractmethod
    def get_primary_master_key(self):
        """
        Returns the primary master key for this MasterKeyProvider.

        :rtype: oci.encryption.MasterKey
        """
        pass

    @abc.abstractmethod
    def get_master_key(self, **kwargs):
        """
        Returns a specific master key based on the arguments provided.

        :rtype: oci.encryption.MasterKey
        """
        pass


class KMSMasterKeyProvider(MasterKeyProvider):
    def __init__(self, config, kms_master_keys=None, **kwargs):
        """
        :param dict config: (required)
            An OCI config dict used to create underlying clients to talk to OCI KMS.
            Note, the 'region' in this config must match the region that the key / vault
            exist in otherwise they will not be found.

        :param list[KMSMasterKey] kms_master_keys: (optional)
            A list of KMSMasterKeys. Currently a max of 1 master key is supported.
            For decryption, you can use a KMSMasterKeyProvder with no master keys.

        :param signer: (optional)
            The signer to use when signing requests made by the service client. The default is to use a :py:class:`~oci.signer.Signer` based on the values
            provided in the config parameter.

            One use case for this parameter is for `Instance Principals authentication <https://docs.cloud.oracle.com/Content/Identity/Tasks/callingservicesfrominstances.htm>`__
            by passing an instance of :py:class:`~oci.auth.signers.InstancePrincipalsSecurityTokenSigner` as the value for this keyword argument
        :type signer: :py:class:`~oci.signer.AbstractBaseSigner`
        """
        if kms_master_keys is not None and len(kms_master_keys) > 1:
            raise ValueError(
                "Only one KMS master key is currently supported for KMSMasterKeyProvider"
            )

        self.primary_master_key = None
        if kms_master_keys:
            self.primary_master_key = kms_master_keys[0]

        self.signer = kwargs.get('signer')
        self.config = config
        if not self.config and not self.signer:
            raise ValueError(
                "Either a config or signer must be passed in"
            )

    def get_primary_master_key(self):
        return self.primary_master_key

    def get_master_key(self, **kwargs):
        """
        Get a KMSMasterKey based on the provided parameters.

        If this key provider already has the KMSMasterKey that was requested, it will return it.
        If it does not have a representation of the KMSMasterKey locally, it will attempt to
        retrieve it from KMS.

        :param str master_key_id: (required)
            The OCID of this master key

        :param str vault_id: (optional)
            The OCID of the vault this master key resides in

        :param str region: (optional)
            The region this master key resides in
        """
        if not kwargs.get("master_key_id"):
            raise ValueError("keyword argument master_key_id must not be None")

        if self.primary_master_key and self.primary_master_key.get_identifier() == kwargs.get(
            "master_key_id"
        ):
            return self.primary_master_key

        master_key_config = self.config

        if self.signer:
            kwargs["signer"] = self.signer

        kms_master_key = KMSMasterKey(config=master_key_config, **kwargs)
        return kms_master_key


@six.add_metaclass(abc.ABCMeta)
class MasterKey(object):
    """
    An abstract base class representing a MasterKey resource to be used in
    encryption and decryption operations.
    """
    @abc.abstractmethod
    def generate_data_encryption_key(self, algorithm):
        """
        Generates a data encryption key (DEK) based on the algorithm provided using
        this MasterKey.  The returned DataEncryptionKey includes a copy of the
        DEK encrypted under this MasterKey.

        :param oci.encryption.algorithms.Algorithm algorithm: (required)
            The algorithm the key will be used for.

        :rtype: oci.encryption.key_providers.DataEncryptionKey
        """
        pass

    @abc.abstractmethod
    def decrypt(self, bytes_to_decrypt):
        """
        Decrypts and returns bytes that were encrypted under this master key.

        :param bytes bytes_to_decrypt: (required)
            The bytes to decrypt using this MasterKey.

        :rtype: bytes
        """
        pass

    @abc.abstractmethod
    def get_identifier(self):
        """
        Returns an identifier for this MasterKey.

        :rtype: str
        """
        pass


class KMSMasterKey(MasterKey):
    def __init__(self, config, master_key_id, vault_id, **kwargs):
        """
        Represents a MasterKey contained in the OCI Key Management Service.

        :param dict config: (required)
            An OCI config dict used to create underlying clients to talk to OCI KMS.
            Note, the 'region' in this config must match the region that the key / vault
            exist in otherwise they will not be found.

        :param str master_key_id: (required)
            The OCID of the KMS master key

        :param str vault_id: (required)
            The OCID of the vault containing the master key

        :param signer: (optional)
            The signer to use when signing requests made by the service client. The default is to use a :py:class:`~oci.signer.Signer` based on the values
            provided in the config parameter.

            One use case for this parameter is for `Instance Principals authentication <https://docs.cloud.oracle.com/Content/Identity/Tasks/callingservicesfrominstances.htm>`__
            by passing an instance of :py:class:`~oci.auth.signers.InstancePrincipalsSecurityTokenSigner` as the value for this keyword argument
        :type signer: :py:class:`~oci.signer.AbstractBaseSigner`

        :param str region: (optional)
            The region this master key resides in
        """
        if not config and not kwargs.get("signer"):
            raise ValueError(
                "Either a config or signer must be passed in"
            )

        self.region = None
        # Get region from **kwargs, config, or signer
        if kwargs.get('region'):
            self.region = kwargs.get("region")
        elif "region" in config:
            self.region = config["region"]
        elif kwargs.get('signer'):
            self.region = kwargs.get("signer").region

        kms_vault_client = KmsVaultClient(config, **kwargs)
        # There is a chance that caller specified a region and differs from the config or signer's region
        kms_vault_client.base_client.set_region(self.region)

        try:
            vault = kms_vault_client.get_vault(vault_id).data
        except ServiceError as service_error:
            message = "Failed to access vaultId: {vault_id} while targeting region: {region}.".format(
                vault_id=vault_id, region=self.region
            )
            raise_runtime_error_from(message, service_error)

        self.kms_management_client = KmsManagementClient(
            config, service_endpoint=vault.management_endpoint, **kwargs
        )

        self.kms_crypto_client = KmsCryptoClient(
            config, service_endpoint=vault.crypto_endpoint, **kwargs
        )

        self.master_key_id = master_key_id
        self.vault_id = vault.id

    def generate_data_encryption_key(self, algorithm):
        dek_key_shape = KeyShape()

        # only AES is currently supported for client side encryption
        if algorithm.algorithm.name != algorithms.AES.name:
            raise ValueError(
                "Only AES is currently supported for client side encryption with KMS master key"
            )

        dek_key_shape.algorithm = KeyShape.ALGORITHM_AES
        dek_key_shape.length = algorithm.key_len

        generate_key_details = GenerateKeyDetails()
        generate_key_details.include_plaintext_key = True
        generate_key_details.key_id = self.master_key_id
        generate_key_details.key_shape = dek_key_shape

        try:
            generated_key = self.kms_crypto_client.generate_data_encryption_key(
                generate_key_details
            ).data
        except ServiceError as service_error:
            message = "Failed to generate data encryption key using masterKeyId: {master_key_id} while targeting vault: {vault_id}.".format(
                master_key_id=self.master_key_id,
                vault_id=self.vault_id
            )
            raise_runtime_error_from(message, service_error)

        dek_plaintext_bytes = base64.b64decode(generated_key.plaintext)
        dek_ciphertext_bytes = base64.b64decode(generated_key.ciphertext)

        return DataEncryptionKey(
            plaintext_key_bytes=dek_plaintext_bytes,
            encrypted_key_bytes=dek_ciphertext_bytes,
            plaintext_key_checksum=generated_key.plaintext_checksum,
        )

    def decrypt(self, bytes_to_decrypt):
        """
        Decrypts and returns bytes that were encrypted under this master key.

        :param bytes bytes_to_decrypt: (required)
            The bytes to decrypt using this MasterKey.

        :rtype: bytes
        """
        decrypt_data_details = DecryptDataDetails()

        # KMS API expects the key base64 encoded
        decrypt_data_details.ciphertext = convert_to_str(
            base64.b64encode(bytes_to_decrypt)
        )
        decrypt_data_details.key_id = self.master_key_id

        try:
            decrypted_data = self.kms_crypto_client.decrypt(decrypt_data_details).data
        except ServiceError as service_error:
            message = "Failed to decrypt data encryption key using masterKeyId: {master_key_id} while targeting vault: {vault_id}.".format(
                master_key_id=self.master_key_id,
                vault_id=self.vault_id
            )
            raise_runtime_error_from(message, service_error)

        verify_crc32_checksum(
            base64.b64decode(decrypted_data.plaintext),
            decrypted_data.plaintext_checksum,
        )

        return decrypted_data.plaintext

    def get_identifier(self):
        """
        Returns the OCID of this master key in the OCI Key Management Service.

        :rtype: str
        """
        return self.master_key_id


class DataEncryptionKey(object):
    """
    Represents a data encryption key used to encrypt and decrypt payloads.
    """
    def __init__(
        self, plaintext_key_bytes, encrypted_key_bytes, plaintext_key_checksum=None
    ):
        """
        :param bytes plaintext_key_bytes:
            The bytes of the data encryption key in plaintext

        :param bytes encrypted_key_bytes:
            The bytes of the data encrypted key encrypted under a master key

        :param str plaintext_key_checksum:
            The crc32 checsum of the plaintext data encryption key
        """
        self.plaintext_key_bytes = plaintext_key_bytes
        self.encrypted_key_bytes = encrypted_key_bytes
        self.plaintext_key_checksum = plaintext_key_checksum

        if self.plaintext_key_checksum:
            verify_crc32_checksum(plaintext_key_bytes, plaintext_key_checksum)
