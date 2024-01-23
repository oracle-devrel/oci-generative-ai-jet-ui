# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class CreateServiceInstanceDetails(object):
    """
    The information about new ServiceInstance.
    """

    #: A constant which can be used with the service_instance_type property of a CreateServiceInstanceDetails.
    #: This constant has a value of "INTEGRATION_CLOUD"
    SERVICE_INSTANCE_TYPE_INTEGRATION_CLOUD = "INTEGRATION_CLOUD"

    #: A constant which can be used with the service_instance_type property of a CreateServiceInstanceDetails.
    #: This constant has a value of "ANALYTICS_WAREHOUSE"
    SERVICE_INSTANCE_TYPE_ANALYTICS_WAREHOUSE = "ANALYTICS_WAREHOUSE"

    def __init__(self, **kwargs):
        """
        Initializes a new CreateServiceInstanceDetails object with values from keyword arguments. This class has the following subclasses and if you are using this class as input
        to a service operations then you should favor using a subclass over the base class:

        * :class:`~oci.fusion_apps.models.CreateOaxServiceInstanceDetails`
        * :class:`~oci.fusion_apps.models.CreateOicServiceInstanceDetails`

        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param display_name:
            The value to assign to the display_name property of this CreateServiceInstanceDetails.
        :type display_name: str

        :param compartment_id:
            The value to assign to the compartment_id property of this CreateServiceInstanceDetails.
        :type compartment_id: str

        :param service_instance_type:
            The value to assign to the service_instance_type property of this CreateServiceInstanceDetails.
            Allowed values for this property are: "INTEGRATION_CLOUD", "ANALYTICS_WAREHOUSE"
        :type service_instance_type: str

        """
        self.swagger_types = {
            'display_name': 'str',
            'compartment_id': 'str',
            'service_instance_type': 'str'
        }

        self.attribute_map = {
            'display_name': 'displayName',
            'compartment_id': 'compartmentId',
            'service_instance_type': 'serviceInstanceType'
        }

        self._display_name = None
        self._compartment_id = None
        self._service_instance_type = None

    @staticmethod
    def get_subtype(object_dictionary):
        """
        Given the hash representation of a subtype of this class,
        use the info in the hash to return the class of the subtype.
        """
        type = object_dictionary['serviceInstanceType']

        if type == 'ANALYTICS_WAREHOUSE':
            return 'CreateOaxServiceInstanceDetails'

        if type == 'INTEGRATION_CLOUD':
            return 'CreateOicServiceInstanceDetails'
        else:
            return 'CreateServiceInstanceDetails'

    @property
    def display_name(self):
        """
        **[Required]** Gets the display_name of this CreateServiceInstanceDetails.
        The service instance type being provisioned


        :return: The display_name of this CreateServiceInstanceDetails.
        :rtype: str
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        """
        Sets the display_name of this CreateServiceInstanceDetails.
        The service instance type being provisioned


        :param display_name: The display_name of this CreateServiceInstanceDetails.
        :type: str
        """
        self._display_name = display_name

    @property
    def compartment_id(self):
        """
        Gets the compartment_id of this CreateServiceInstanceDetails.
        Comparment where the instance is to be created


        :return: The compartment_id of this CreateServiceInstanceDetails.
        :rtype: str
        """
        return self._compartment_id

    @compartment_id.setter
    def compartment_id(self, compartment_id):
        """
        Sets the compartment_id of this CreateServiceInstanceDetails.
        Comparment where the instance is to be created


        :param compartment_id: The compartment_id of this CreateServiceInstanceDetails.
        :type: str
        """
        self._compartment_id = compartment_id

    @property
    def service_instance_type(self):
        """
        **[Required]** Gets the service_instance_type of this CreateServiceInstanceDetails.
        Type of the ServiceInstance.

        Allowed values for this property are: "INTEGRATION_CLOUD", "ANALYTICS_WAREHOUSE"


        :return: The service_instance_type of this CreateServiceInstanceDetails.
        :rtype: str
        """
        return self._service_instance_type

    @service_instance_type.setter
    def service_instance_type(self, service_instance_type):
        """
        Sets the service_instance_type of this CreateServiceInstanceDetails.
        Type of the ServiceInstance.


        :param service_instance_type: The service_instance_type of this CreateServiceInstanceDetails.
        :type: str
        """
        allowed_values = ["INTEGRATION_CLOUD", "ANALYTICS_WAREHOUSE"]
        if not value_allowed_none_or_none_sentinel(service_instance_type, allowed_values):
            raise ValueError(
                "Invalid value for `service_instance_type`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._service_instance_type = service_instance_type

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
