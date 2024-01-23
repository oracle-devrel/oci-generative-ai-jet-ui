# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .create_service_instance_details import CreateServiceInstanceDetails
from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class CreateOicServiceInstanceDetails(CreateServiceInstanceDetails):
    """
    The information about new Integration Cloud instance being provisioned.
    """

    #: A constant which can be used with the edition property of a CreateOicServiceInstanceDetails.
    #: This constant has a value of "STANDARD"
    EDITION_STANDARD = "STANDARD"

    #: A constant which can be used with the edition property of a CreateOicServiceInstanceDetails.
    #: This constant has a value of "ENTERPRISE"
    EDITION_ENTERPRISE = "ENTERPRISE"

    def __init__(self, **kwargs):
        """
        Initializes a new CreateOicServiceInstanceDetails object with values from keyword arguments. The default value of the :py:attr:`~oci.fusion_apps.models.CreateOicServiceInstanceDetails.service_instance_type` attribute
        of this class is ``INTEGRATION_CLOUD`` and it should not be changed.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param display_name:
            The value to assign to the display_name property of this CreateOicServiceInstanceDetails.
        :type display_name: str

        :param compartment_id:
            The value to assign to the compartment_id property of this CreateOicServiceInstanceDetails.
        :type compartment_id: str

        :param service_instance_type:
            The value to assign to the service_instance_type property of this CreateOicServiceInstanceDetails.
            Allowed values for this property are: "INTEGRATION_CLOUD", "ANALYTICS_WAREHOUSE"
        :type service_instance_type: str

        :param message_packs:
            The value to assign to the message_packs property of this CreateOicServiceInstanceDetails.
        :type message_packs: int

        :param edition:
            The value to assign to the edition property of this CreateOicServiceInstanceDetails.
            Allowed values for this property are: "STANDARD", "ENTERPRISE"
        :type edition: str

        """
        self.swagger_types = {
            'display_name': 'str',
            'compartment_id': 'str',
            'service_instance_type': 'str',
            'message_packs': 'int',
            'edition': 'str'
        }

        self.attribute_map = {
            'display_name': 'displayName',
            'compartment_id': 'compartmentId',
            'service_instance_type': 'serviceInstanceType',
            'message_packs': 'messagePacks',
            'edition': 'edition'
        }

        self._display_name = None
        self._compartment_id = None
        self._service_instance_type = None
        self._message_packs = None
        self._edition = None
        self._service_instance_type = 'INTEGRATION_CLOUD'

    @property
    def message_packs(self):
        """
        Gets the message_packs of this CreateOicServiceInstanceDetails.
        Number of 5K message packs per hour


        :return: The message_packs of this CreateOicServiceInstanceDetails.
        :rtype: int
        """
        return self._message_packs

    @message_packs.setter
    def message_packs(self, message_packs):
        """
        Sets the message_packs of this CreateOicServiceInstanceDetails.
        Number of 5K message packs per hour


        :param message_packs: The message_packs of this CreateOicServiceInstanceDetails.
        :type: int
        """
        self._message_packs = message_packs

    @property
    def edition(self):
        """
        Gets the edition of this CreateOicServiceInstanceDetails.
        The   Oracle Integration edition

        Allowed values for this property are: "STANDARD", "ENTERPRISE"


        :return: The edition of this CreateOicServiceInstanceDetails.
        :rtype: str
        """
        return self._edition

    @edition.setter
    def edition(self, edition):
        """
        Sets the edition of this CreateOicServiceInstanceDetails.
        The   Oracle Integration edition


        :param edition: The edition of this CreateOicServiceInstanceDetails.
        :type: str
        """
        allowed_values = ["STANDARD", "ENTERPRISE"]
        if not value_allowed_none_or_none_sentinel(edition, allowed_values):
            raise ValueError(
                "Invalid value for `edition`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._edition = edition

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
