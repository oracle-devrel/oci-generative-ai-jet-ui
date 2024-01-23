# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .create_service_instance_details import CreateServiceInstanceDetails
from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class CreateOaxServiceInstanceDetails(CreateServiceInstanceDetails):
    """
    The information about new Analytics Warehouse instance being provisioned.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new CreateOaxServiceInstanceDetails object with values from keyword arguments. The default value of the :py:attr:`~oci.fusion_apps.models.CreateOaxServiceInstanceDetails.service_instance_type` attribute
        of this class is ``ANALYTICS_WAREHOUSE`` and it should not be changed.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param display_name:
            The value to assign to the display_name property of this CreateOaxServiceInstanceDetails.
        :type display_name: str

        :param compartment_id:
            The value to assign to the compartment_id property of this CreateOaxServiceInstanceDetails.
        :type compartment_id: str

        :param service_instance_type:
            The value to assign to the service_instance_type property of this CreateOaxServiceInstanceDetails.
            Allowed values for this property are: "INTEGRATION_CLOUD", "ANALYTICS_WAREHOUSE"
        :type service_instance_type: str

        :param name:
            The value to assign to the name property of this CreateOaxServiceInstanceDetails.
        :type name: str

        :param description:
            The value to assign to the description property of this CreateOaxServiceInstanceDetails.
        :type description: str

        :param faw_admin_info:
            The value to assign to the faw_admin_info property of this CreateOaxServiceInstanceDetails.
        :type faw_admin_info: oci.fusion_apps.models.FawAdminInfoDetails

        """
        self.swagger_types = {
            'display_name': 'str',
            'compartment_id': 'str',
            'service_instance_type': 'str',
            'name': 'str',
            'description': 'str',
            'faw_admin_info': 'FawAdminInfoDetails'
        }

        self.attribute_map = {
            'display_name': 'displayName',
            'compartment_id': 'compartmentId',
            'service_instance_type': 'serviceInstanceType',
            'name': 'name',
            'description': 'description',
            'faw_admin_info': 'FawAdminInfo'
        }

        self._display_name = None
        self._compartment_id = None
        self._service_instance_type = None
        self._name = None
        self._description = None
        self._faw_admin_info = None
        self._service_instance_type = 'ANALYTICS_WAREHOUSE'

    @property
    def name(self):
        """
        **[Required]** Gets the name of this CreateOaxServiceInstanceDetails.
        A unique Name for Analytics Warehouse.


        :return: The name of this CreateOaxServiceInstanceDetails.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Sets the name of this CreateOaxServiceInstanceDetails.
        A unique Name for Analytics Warehouse.


        :param name: The name of this CreateOaxServiceInstanceDetails.
        :type: str
        """
        self._name = name

    @property
    def description(self):
        """
        Gets the description of this CreateOaxServiceInstanceDetails.
        This is the description for Analytics Warehouse Service.


        :return: The description of this CreateOaxServiceInstanceDetails.
        :rtype: str
        """
        return self._description

    @description.setter
    def description(self, description):
        """
        Sets the description of this CreateOaxServiceInstanceDetails.
        This is the description for Analytics Warehouse Service.


        :param description: The description of this CreateOaxServiceInstanceDetails.
        :type: str
        """
        self._description = description

    @property
    def faw_admin_info(self):
        """
        Gets the faw_admin_info of this CreateOaxServiceInstanceDetails.

        :return: The faw_admin_info of this CreateOaxServiceInstanceDetails.
        :rtype: oci.fusion_apps.models.FawAdminInfoDetails
        """
        return self._faw_admin_info

    @faw_admin_info.setter
    def faw_admin_info(self, faw_admin_info):
        """
        Sets the faw_admin_info of this CreateOaxServiceInstanceDetails.

        :param faw_admin_info: The faw_admin_info of this CreateOaxServiceInstanceDetails.
        :type: oci.fusion_apps.models.FawAdminInfoDetails
        """
        self._faw_admin_info = faw_admin_info

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
