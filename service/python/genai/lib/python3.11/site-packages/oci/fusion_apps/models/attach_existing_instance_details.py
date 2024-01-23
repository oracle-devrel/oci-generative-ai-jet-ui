# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .create_service_attachment_details import CreateServiceAttachmentDetails
from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class AttachExistingInstanceDetails(CreateServiceAttachmentDetails):
    """
    Information about the service attachment.
    """

    #: A constant which can be used with the service_instance_type property of a AttachExistingInstanceDetails.
    #: This constant has a value of "INTEGRATION_CLOUD"
    SERVICE_INSTANCE_TYPE_INTEGRATION_CLOUD = "INTEGRATION_CLOUD"

    #: A constant which can be used with the service_instance_type property of a AttachExistingInstanceDetails.
    #: This constant has a value of "ANALYTICS_WAREHOUSE"
    SERVICE_INSTANCE_TYPE_ANALYTICS_WAREHOUSE = "ANALYTICS_WAREHOUSE"

    def __init__(self, **kwargs):
        """
        Initializes a new AttachExistingInstanceDetails object with values from keyword arguments. The default value of the :py:attr:`~oci.fusion_apps.models.AttachExistingInstanceDetails.action` attribute
        of this class is ``ATTACH_EXISTING_INSTANCE`` and it should not be changed.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param action:
            The value to assign to the action property of this AttachExistingInstanceDetails.
            Allowed values for this property are: "CREATE_NEW_INSTANCE", "ATTACH_EXISTING_INSTANCE"
        :type action: str

        :param service_instance_type:
            The value to assign to the service_instance_type property of this AttachExistingInstanceDetails.
            Allowed values for this property are: "INTEGRATION_CLOUD", "ANALYTICS_WAREHOUSE"
        :type service_instance_type: str

        :param instance_id:
            The value to assign to the instance_id property of this AttachExistingInstanceDetails.
        :type instance_id: str

        :param freeform_tags:
            The value to assign to the freeform_tags property of this AttachExistingInstanceDetails.
        :type freeform_tags: dict(str, str)

        :param defined_tags:
            The value to assign to the defined_tags property of this AttachExistingInstanceDetails.
        :type defined_tags: dict(str, dict(str, object))

        """
        self.swagger_types = {
            'action': 'str',
            'service_instance_type': 'str',
            'instance_id': 'str',
            'freeform_tags': 'dict(str, str)',
            'defined_tags': 'dict(str, dict(str, object))'
        }

        self.attribute_map = {
            'action': 'action',
            'service_instance_type': 'serviceInstanceType',
            'instance_id': 'instanceId',
            'freeform_tags': 'freeformTags',
            'defined_tags': 'definedTags'
        }

        self._action = None
        self._service_instance_type = None
        self._instance_id = None
        self._freeform_tags = None
        self._defined_tags = None
        self._action = 'ATTACH_EXISTING_INSTANCE'

    @property
    def service_instance_type(self):
        """
        **[Required]** Gets the service_instance_type of this AttachExistingInstanceDetails.
        Type of the ServiceInstance being attached.

        Allowed values for this property are: "INTEGRATION_CLOUD", "ANALYTICS_WAREHOUSE"


        :return: The service_instance_type of this AttachExistingInstanceDetails.
        :rtype: str
        """
        return self._service_instance_type

    @service_instance_type.setter
    def service_instance_type(self, service_instance_type):
        """
        Sets the service_instance_type of this AttachExistingInstanceDetails.
        Type of the ServiceInstance being attached.


        :param service_instance_type: The service_instance_type of this AttachExistingInstanceDetails.
        :type: str
        """
        allowed_values = ["INTEGRATION_CLOUD", "ANALYTICS_WAREHOUSE"]
        if not value_allowed_none_or_none_sentinel(service_instance_type, allowed_values):
            raise ValueError(
                "Invalid value for `service_instance_type`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._service_instance_type = service_instance_type

    @property
    def instance_id(self):
        """
        **[Required]** Gets the instance_id of this AttachExistingInstanceDetails.
        The service instance OCID of the instance being attached


        :return: The instance_id of this AttachExistingInstanceDetails.
        :rtype: str
        """
        return self._instance_id

    @instance_id.setter
    def instance_id(self, instance_id):
        """
        Sets the instance_id of this AttachExistingInstanceDetails.
        The service instance OCID of the instance being attached


        :param instance_id: The instance_id of this AttachExistingInstanceDetails.
        :type: str
        """
        self._instance_id = instance_id

    @property
    def freeform_tags(self):
        """
        Gets the freeform_tags of this AttachExistingInstanceDetails.
        Simple key-value pair that is applied without any predefined name, type or scope. Exists for cross-compatibility only.
        Example: `{\"bar-key\": \"value\"}`


        :return: The freeform_tags of this AttachExistingInstanceDetails.
        :rtype: dict(str, str)
        """
        return self._freeform_tags

    @freeform_tags.setter
    def freeform_tags(self, freeform_tags):
        """
        Sets the freeform_tags of this AttachExistingInstanceDetails.
        Simple key-value pair that is applied without any predefined name, type or scope. Exists for cross-compatibility only.
        Example: `{\"bar-key\": \"value\"}`


        :param freeform_tags: The freeform_tags of this AttachExistingInstanceDetails.
        :type: dict(str, str)
        """
        self._freeform_tags = freeform_tags

    @property
    def defined_tags(self):
        """
        Gets the defined_tags of this AttachExistingInstanceDetails.
        Defined tags for this resource. Each key is predefined and scoped to a namespace.
        Example: `{\"foo-namespace\": {\"bar-key\": \"value\"}}`


        :return: The defined_tags of this AttachExistingInstanceDetails.
        :rtype: dict(str, dict(str, object))
        """
        return self._defined_tags

    @defined_tags.setter
    def defined_tags(self, defined_tags):
        """
        Sets the defined_tags of this AttachExistingInstanceDetails.
        Defined tags for this resource. Each key is predefined and scoped to a namespace.
        Example: `{\"foo-namespace\": {\"bar-key\": \"value\"}}`


        :param defined_tags: The defined_tags of this AttachExistingInstanceDetails.
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
