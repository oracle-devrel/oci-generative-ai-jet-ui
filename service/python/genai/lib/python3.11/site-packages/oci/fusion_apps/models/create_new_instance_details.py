# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .create_service_attachment_details import CreateServiceAttachmentDetails
from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class CreateNewInstanceDetails(CreateServiceAttachmentDetails):
    """
    Information about the service attachment.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new CreateNewInstanceDetails object with values from keyword arguments. The default value of the :py:attr:`~oci.fusion_apps.models.CreateNewInstanceDetails.action` attribute
        of this class is ``CREATE_NEW_INSTANCE`` and it should not be changed.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param action:
            The value to assign to the action property of this CreateNewInstanceDetails.
            Allowed values for this property are: "CREATE_NEW_INSTANCE", "ATTACH_EXISTING_INSTANCE"
        :type action: str

        :param details:
            The value to assign to the details property of this CreateNewInstanceDetails.
        :type details: oci.fusion_apps.models.CreateServiceInstanceDetails

        :param freeform_tags:
            The value to assign to the freeform_tags property of this CreateNewInstanceDetails.
        :type freeform_tags: dict(str, str)

        :param defined_tags:
            The value to assign to the defined_tags property of this CreateNewInstanceDetails.
        :type defined_tags: dict(str, dict(str, object))

        """
        self.swagger_types = {
            'action': 'str',
            'details': 'CreateServiceInstanceDetails',
            'freeform_tags': 'dict(str, str)',
            'defined_tags': 'dict(str, dict(str, object))'
        }

        self.attribute_map = {
            'action': 'action',
            'details': 'details',
            'freeform_tags': 'freeformTags',
            'defined_tags': 'definedTags'
        }

        self._action = None
        self._details = None
        self._freeform_tags = None
        self._defined_tags = None
        self._action = 'CREATE_NEW_INSTANCE'

    @property
    def details(self):
        """
        **[Required]** Gets the details of this CreateNewInstanceDetails.

        :return: The details of this CreateNewInstanceDetails.
        :rtype: oci.fusion_apps.models.CreateServiceInstanceDetails
        """
        return self._details

    @details.setter
    def details(self, details):
        """
        Sets the details of this CreateNewInstanceDetails.

        :param details: The details of this CreateNewInstanceDetails.
        :type: oci.fusion_apps.models.CreateServiceInstanceDetails
        """
        self._details = details

    @property
    def freeform_tags(self):
        """
        Gets the freeform_tags of this CreateNewInstanceDetails.
        Simple key-value pair that is applied without any predefined name, type or scope. Exists for cross-compatibility only.
        Example: `{\"bar-key\": \"value\"}`


        :return: The freeform_tags of this CreateNewInstanceDetails.
        :rtype: dict(str, str)
        """
        return self._freeform_tags

    @freeform_tags.setter
    def freeform_tags(self, freeform_tags):
        """
        Sets the freeform_tags of this CreateNewInstanceDetails.
        Simple key-value pair that is applied without any predefined name, type or scope. Exists for cross-compatibility only.
        Example: `{\"bar-key\": \"value\"}`


        :param freeform_tags: The freeform_tags of this CreateNewInstanceDetails.
        :type: dict(str, str)
        """
        self._freeform_tags = freeform_tags

    @property
    def defined_tags(self):
        """
        Gets the defined_tags of this CreateNewInstanceDetails.
        Defined tags for this resource. Each key is predefined and scoped to a namespace.
        Example: `{\"foo-namespace\": {\"bar-key\": \"value\"}}`


        :return: The defined_tags of this CreateNewInstanceDetails.
        :rtype: dict(str, dict(str, object))
        """
        return self._defined_tags

    @defined_tags.setter
    def defined_tags(self, defined_tags):
        """
        Sets the defined_tags of this CreateNewInstanceDetails.
        Defined tags for this resource. Each key is predefined and scoped to a namespace.
        Example: `{\"foo-namespace\": {\"bar-key\": \"value\"}}`


        :param defined_tags: The defined_tags of this CreateNewInstanceDetails.
        :type: dict(str, dict(str, object))
        """
        self._defined_tags = defined_tags

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
