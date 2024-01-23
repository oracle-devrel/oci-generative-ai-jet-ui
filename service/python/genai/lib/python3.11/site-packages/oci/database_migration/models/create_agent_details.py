# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class CreateAgentDetails(object):
    """
    ODMS Agent Details
    """

    def __init__(self, **kwargs):
        """
        Initializes a new CreateAgentDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param compartment_id:
            The value to assign to the compartment_id property of this CreateAgentDetails.
        :type compartment_id: str

        :param display_name:
            The value to assign to the display_name property of this CreateAgentDetails.
        :type display_name: str

        :param stream_id:
            The value to assign to the stream_id property of this CreateAgentDetails.
        :type stream_id: str

        :param public_key:
            The value to assign to the public_key property of this CreateAgentDetails.
        :type public_key: str

        :param version:
            The value to assign to the version property of this CreateAgentDetails.
        :type version: str

        :param freeform_tags:
            The value to assign to the freeform_tags property of this CreateAgentDetails.
        :type freeform_tags: dict(str, str)

        :param defined_tags:
            The value to assign to the defined_tags property of this CreateAgentDetails.
        :type defined_tags: dict(str, dict(str, object))

        """
        self.swagger_types = {
            'compartment_id': 'str',
            'display_name': 'str',
            'stream_id': 'str',
            'public_key': 'str',
            'version': 'str',
            'freeform_tags': 'dict(str, str)',
            'defined_tags': 'dict(str, dict(str, object))'
        }

        self.attribute_map = {
            'compartment_id': 'compartmentId',
            'display_name': 'displayName',
            'stream_id': 'streamId',
            'public_key': 'publicKey',
            'version': 'version',
            'freeform_tags': 'freeformTags',
            'defined_tags': 'definedTags'
        }

        self._compartment_id = None
        self._display_name = None
        self._stream_id = None
        self._public_key = None
        self._version = None
        self._freeform_tags = None
        self._defined_tags = None

    @property
    def compartment_id(self):
        """
        **[Required]** Gets the compartment_id of this CreateAgentDetails.
        The OCID of the compartment.


        :return: The compartment_id of this CreateAgentDetails.
        :rtype: str
        """
        return self._compartment_id

    @compartment_id.setter
    def compartment_id(self, compartment_id):
        """
        Sets the compartment_id of this CreateAgentDetails.
        The OCID of the compartment.


        :param compartment_id: The compartment_id of this CreateAgentDetails.
        :type: str
        """
        self._compartment_id = compartment_id

    @property
    def display_name(self):
        """
        **[Required]** Gets the display_name of this CreateAgentDetails.
        ODMS Agent name


        :return: The display_name of this CreateAgentDetails.
        :rtype: str
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        """
        Sets the display_name of this CreateAgentDetails.
        ODMS Agent name


        :param display_name: The display_name of this CreateAgentDetails.
        :type: str
        """
        self._display_name = display_name

    @property
    def stream_id(self):
        """
        **[Required]** Gets the stream_id of this CreateAgentDetails.
        The OCID of the Stream


        :return: The stream_id of this CreateAgentDetails.
        :rtype: str
        """
        return self._stream_id

    @stream_id.setter
    def stream_id(self, stream_id):
        """
        Sets the stream_id of this CreateAgentDetails.
        The OCID of the Stream


        :param stream_id: The stream_id of this CreateAgentDetails.
        :type: str
        """
        self._stream_id = stream_id

    @property
    def public_key(self):
        """
        **[Required]** Gets the public_key of this CreateAgentDetails.
        ODMS Agent public key as a Base64 Encoded string.


        :return: The public_key of this CreateAgentDetails.
        :rtype: str
        """
        return self._public_key

    @public_key.setter
    def public_key(self, public_key):
        """
        Sets the public_key of this CreateAgentDetails.
        ODMS Agent public key as a Base64 Encoded string.


        :param public_key: The public_key of this CreateAgentDetails.
        :type: str
        """
        self._public_key = public_key

    @property
    def version(self):
        """
        **[Required]** Gets the version of this CreateAgentDetails.
        ODMS Agent version


        :return: The version of this CreateAgentDetails.
        :rtype: str
        """
        return self._version

    @version.setter
    def version(self, version):
        """
        Sets the version of this CreateAgentDetails.
        ODMS Agent version


        :param version: The version of this CreateAgentDetails.
        :type: str
        """
        self._version = version

    @property
    def freeform_tags(self):
        """
        Gets the freeform_tags of this CreateAgentDetails.
        Simple key-value pair that is applied without any predefined name, type or scope. Exists for cross-compatibility only.
        Example: `{\"bar-key\": \"value\"}`


        :return: The freeform_tags of this CreateAgentDetails.
        :rtype: dict(str, str)
        """
        return self._freeform_tags

    @freeform_tags.setter
    def freeform_tags(self, freeform_tags):
        """
        Sets the freeform_tags of this CreateAgentDetails.
        Simple key-value pair that is applied without any predefined name, type or scope. Exists for cross-compatibility only.
        Example: `{\"bar-key\": \"value\"}`


        :param freeform_tags: The freeform_tags of this CreateAgentDetails.
        :type: dict(str, str)
        """
        self._freeform_tags = freeform_tags

    @property
    def defined_tags(self):
        """
        Gets the defined_tags of this CreateAgentDetails.
        Defined tags for this resource. Each key is predefined and scoped to a namespace.
        Example: `{\"foo-namespace\": {\"bar-key\": \"value\"}}`


        :return: The defined_tags of this CreateAgentDetails.
        :rtype: dict(str, dict(str, object))
        """
        return self._defined_tags

    @defined_tags.setter
    def defined_tags(self, defined_tags):
        """
        Sets the defined_tags of this CreateAgentDetails.
        Defined tags for this resource. Each key is predefined and scoped to a namespace.
        Example: `{\"foo-namespace\": {\"bar-key\": \"value\"}}`


        :param defined_tags: The defined_tags of this CreateAgentDetails.
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
