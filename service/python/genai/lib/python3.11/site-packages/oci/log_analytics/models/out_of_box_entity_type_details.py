# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class OutOfBoxEntityTypeDetails(object):
    """
    A Single Entity Type Definition
    """

    #: A constant which can be used with the cloud_type property of a OutOfBoxEntityTypeDetails.
    #: This constant has a value of "CLOUD"
    CLOUD_TYPE_CLOUD = "CLOUD"

    #: A constant which can be used with the cloud_type property of a OutOfBoxEntityTypeDetails.
    #: This constant has a value of "NON_CLOUD"
    CLOUD_TYPE_NON_CLOUD = "NON_CLOUD"

    def __init__(self, **kwargs):
        """
        Initializes a new OutOfBoxEntityTypeDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param name:
            The value to assign to the name property of this OutOfBoxEntityTypeDetails.
        :type name: str

        :param internal_name:
            The value to assign to the internal_name property of this OutOfBoxEntityTypeDetails.
        :type internal_name: str

        :param category:
            The value to assign to the category property of this OutOfBoxEntityTypeDetails.
        :type category: str

        :param cloud_type:
            The value to assign to the cloud_type property of this OutOfBoxEntityTypeDetails.
            Allowed values for this property are: "CLOUD", "NON_CLOUD"
        :type cloud_type: str

        :param properties:
            The value to assign to the properties property of this OutOfBoxEntityTypeDetails.
        :type properties: list[EntityTypeProperty]

        """
        self.swagger_types = {
            'name': 'str',
            'internal_name': 'str',
            'category': 'str',
            'cloud_type': 'str',
            'properties': 'list[EntityTypeProperty]'
        }

        self.attribute_map = {
            'name': 'name',
            'internal_name': 'internalName',
            'category': 'category',
            'cloud_type': 'cloudType',
            'properties': 'properties'
        }

        self._name = None
        self._internal_name = None
        self._category = None
        self._cloud_type = None
        self._properties = None

    @property
    def name(self):
        """
        **[Required]** Gets the name of this OutOfBoxEntityTypeDetails.
        Log analytics entity type name.


        :return: The name of this OutOfBoxEntityTypeDetails.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Sets the name of this OutOfBoxEntityTypeDetails.
        Log analytics entity type name.


        :param name: The name of this OutOfBoxEntityTypeDetails.
        :type: str
        """
        self._name = name

    @property
    def internal_name(self):
        """
        **[Required]** Gets the internal_name of this OutOfBoxEntityTypeDetails.
        Internal name for the log analytics entity type.


        :return: The internal_name of this OutOfBoxEntityTypeDetails.
        :rtype: str
        """
        return self._internal_name

    @internal_name.setter
    def internal_name(self, internal_name):
        """
        Sets the internal_name of this OutOfBoxEntityTypeDetails.
        Internal name for the log analytics entity type.


        :param internal_name: The internal_name of this OutOfBoxEntityTypeDetails.
        :type: str
        """
        self._internal_name = internal_name

    @property
    def category(self):
        """
        **[Required]** Gets the category of this OutOfBoxEntityTypeDetails.
        Log analytics entity type category. Category will be used for grouping and filtering.


        :return: The category of this OutOfBoxEntityTypeDetails.
        :rtype: str
        """
        return self._category

    @category.setter
    def category(self, category):
        """
        Sets the category of this OutOfBoxEntityTypeDetails.
        Log analytics entity type category. Category will be used for grouping and filtering.


        :param category: The category of this OutOfBoxEntityTypeDetails.
        :type: str
        """
        self._category = category

    @property
    def cloud_type(self):
        """
        **[Required]** Gets the cloud_type of this OutOfBoxEntityTypeDetails.
        Log analytics entity type group. Supported values: ClOUD, NON_CLOUD.

        Allowed values for this property are: "CLOUD", "NON_CLOUD"


        :return: The cloud_type of this OutOfBoxEntityTypeDetails.
        :rtype: str
        """
        return self._cloud_type

    @cloud_type.setter
    def cloud_type(self, cloud_type):
        """
        Sets the cloud_type of this OutOfBoxEntityTypeDetails.
        Log analytics entity type group. Supported values: ClOUD, NON_CLOUD.


        :param cloud_type: The cloud_type of this OutOfBoxEntityTypeDetails.
        :type: str
        """
        allowed_values = ["CLOUD", "NON_CLOUD"]
        if not value_allowed_none_or_none_sentinel(cloud_type, allowed_values):
            raise ValueError(
                "Invalid value for `cloud_type`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._cloud_type = cloud_type

    @property
    def properties(self):
        """
        Gets the properties of this OutOfBoxEntityTypeDetails.
        A Single Entity Type Property Definition


        :return: The properties of this OutOfBoxEntityTypeDetails.
        :rtype: list[EntityTypeProperty]
        """
        return self._properties

    @properties.setter
    def properties(self, properties):
        """
        Sets the properties of this OutOfBoxEntityTypeDetails.
        A Single Entity Type Property Definition


        :param properties: The properties of this OutOfBoxEntityTypeDetails.
        :type: list[EntityTypeProperty]
        """
        self._properties = properties

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
