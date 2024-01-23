# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .create_data_asset_details import CreateDataAssetDetails
from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class CreateDataAssetFromLakehouse(CreateDataAssetDetails):
    """
    Details for the Lakehouse data asset type.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new CreateDataAssetFromLakehouse object with values from keyword arguments. The default value of the :py:attr:`~oci.data_integration.models.CreateDataAssetFromLakehouse.model_type` attribute
        of this class is ``LAKE_HOUSE_DATA_ASSET`` and it should not be changed.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param model_type:
            The value to assign to the model_type property of this CreateDataAssetFromLakehouse.
            Allowed values for this property are: "ORACLE_DATA_ASSET", "ORACLE_OBJECT_STORAGE_DATA_ASSET", "ORACLE_ATP_DATA_ASSET", "ORACLE_ADWC_DATA_ASSET", "MYSQL_DATA_ASSET", "GENERIC_JDBC_DATA_ASSET", "FUSION_APP_DATA_ASSET", "AMAZON_S3_DATA_ASSET", "LAKE_HOUSE_DATA_ASSET", "REST_DATA_ASSET"
        :type model_type: str

        :param key:
            The value to assign to the key property of this CreateDataAssetFromLakehouse.
        :type key: str

        :param model_version:
            The value to assign to the model_version property of this CreateDataAssetFromLakehouse.
        :type model_version: str

        :param name:
            The value to assign to the name property of this CreateDataAssetFromLakehouse.
        :type name: str

        :param description:
            The value to assign to the description property of this CreateDataAssetFromLakehouse.
        :type description: str

        :param object_status:
            The value to assign to the object_status property of this CreateDataAssetFromLakehouse.
        :type object_status: int

        :param identifier:
            The value to assign to the identifier property of this CreateDataAssetFromLakehouse.
        :type identifier: str

        :param external_key:
            The value to assign to the external_key property of this CreateDataAssetFromLakehouse.
        :type external_key: str

        :param asset_properties:
            The value to assign to the asset_properties property of this CreateDataAssetFromLakehouse.
        :type asset_properties: dict(str, str)

        :param registry_metadata:
            The value to assign to the registry_metadata property of this CreateDataAssetFromLakehouse.
        :type registry_metadata: oci.data_integration.models.RegistryMetadata

        :param lakehouse_ocid:
            The value to assign to the lakehouse_ocid property of this CreateDataAssetFromLakehouse.
        :type lakehouse_ocid: str

        :param metastore_id:
            The value to assign to the metastore_id property of this CreateDataAssetFromLakehouse.
        :type metastore_id: str

        :param ranger_endpoint:
            The value to assign to the ranger_endpoint property of this CreateDataAssetFromLakehouse.
        :type ranger_endpoint: str

        :param default_connection:
            The value to assign to the default_connection property of this CreateDataAssetFromLakehouse.
        :type default_connection: oci.data_integration.models.CreateConnectionFromLakehouse

        """
        self.swagger_types = {
            'model_type': 'str',
            'key': 'str',
            'model_version': 'str',
            'name': 'str',
            'description': 'str',
            'object_status': 'int',
            'identifier': 'str',
            'external_key': 'str',
            'asset_properties': 'dict(str, str)',
            'registry_metadata': 'RegistryMetadata',
            'lakehouse_ocid': 'str',
            'metastore_id': 'str',
            'ranger_endpoint': 'str',
            'default_connection': 'CreateConnectionFromLakehouse'
        }

        self.attribute_map = {
            'model_type': 'modelType',
            'key': 'key',
            'model_version': 'modelVersion',
            'name': 'name',
            'description': 'description',
            'object_status': 'objectStatus',
            'identifier': 'identifier',
            'external_key': 'externalKey',
            'asset_properties': 'assetProperties',
            'registry_metadata': 'registryMetadata',
            'lakehouse_ocid': 'lakehouseOcid',
            'metastore_id': 'metastoreId',
            'ranger_endpoint': 'rangerEndpoint',
            'default_connection': 'defaultConnection'
        }

        self._model_type = None
        self._key = None
        self._model_version = None
        self._name = None
        self._description = None
        self._object_status = None
        self._identifier = None
        self._external_key = None
        self._asset_properties = None
        self._registry_metadata = None
        self._lakehouse_ocid = None
        self._metastore_id = None
        self._ranger_endpoint = None
        self._default_connection = None
        self._model_type = 'LAKE_HOUSE_DATA_ASSET'

    @property
    def lakehouse_ocid(self):
        """
        **[Required]** Gets the lakehouse_ocid of this CreateDataAssetFromLakehouse.
        The Lakehouse Ocid.


        :return: The lakehouse_ocid of this CreateDataAssetFromLakehouse.
        :rtype: str
        """
        return self._lakehouse_ocid

    @lakehouse_ocid.setter
    def lakehouse_ocid(self, lakehouse_ocid):
        """
        Sets the lakehouse_ocid of this CreateDataAssetFromLakehouse.
        The Lakehouse Ocid.


        :param lakehouse_ocid: The lakehouse_ocid of this CreateDataAssetFromLakehouse.
        :type: str
        """
        self._lakehouse_ocid = lakehouse_ocid

    @property
    def metastore_id(self):
        """
        Gets the metastore_id of this CreateDataAssetFromLakehouse.
        The metastoreId for the specified Lakehouse Resource.


        :return: The metastore_id of this CreateDataAssetFromLakehouse.
        :rtype: str
        """
        return self._metastore_id

    @metastore_id.setter
    def metastore_id(self, metastore_id):
        """
        Sets the metastore_id of this CreateDataAssetFromLakehouse.
        The metastoreId for the specified Lakehouse Resource.


        :param metastore_id: The metastore_id of this CreateDataAssetFromLakehouse.
        :type: str
        """
        self._metastore_id = metastore_id

    @property
    def ranger_endpoint(self):
        """
        Gets the ranger_endpoint of this CreateDataAssetFromLakehouse.
        The rangerEndpoint for the specified Lakehouse Resource.


        :return: The ranger_endpoint of this CreateDataAssetFromLakehouse.
        :rtype: str
        """
        return self._ranger_endpoint

    @ranger_endpoint.setter
    def ranger_endpoint(self, ranger_endpoint):
        """
        Sets the ranger_endpoint of this CreateDataAssetFromLakehouse.
        The rangerEndpoint for the specified Lakehouse Resource.


        :param ranger_endpoint: The ranger_endpoint of this CreateDataAssetFromLakehouse.
        :type: str
        """
        self._ranger_endpoint = ranger_endpoint

    @property
    def default_connection(self):
        """
        **[Required]** Gets the default_connection of this CreateDataAssetFromLakehouse.

        :return: The default_connection of this CreateDataAssetFromLakehouse.
        :rtype: oci.data_integration.models.CreateConnectionFromLakehouse
        """
        return self._default_connection

    @default_connection.setter
    def default_connection(self, default_connection):
        """
        Sets the default_connection of this CreateDataAssetFromLakehouse.

        :param default_connection: The default_connection of this CreateDataAssetFromLakehouse.
        :type: oci.data_integration.models.CreateConnectionFromLakehouse
        """
        self._default_connection = default_connection

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
