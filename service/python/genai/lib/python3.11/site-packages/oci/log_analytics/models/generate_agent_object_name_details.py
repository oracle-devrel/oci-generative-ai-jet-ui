# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class GenerateAgentObjectNameDetails(object):
    """
    Generate agent upload name for the given properties
    """

    def __init__(self, **kwargs):
        """
        Initializes a new GenerateAgentObjectNameDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param log_group_id:
            The value to assign to the log_group_id property of this GenerateAgentObjectNameDetails.
        :type log_group_id: str

        :param unique_id:
            The value to assign to the unique_id property of this GenerateAgentObjectNameDetails.
        :type unique_id: str

        :param meta_properties:
            The value to assign to the meta_properties property of this GenerateAgentObjectNameDetails.
        :type meta_properties: str

        :param time_created:
            The value to assign to the time_created property of this GenerateAgentObjectNameDetails.
        :type time_created: datetime

        """
        self.swagger_types = {
            'log_group_id': 'str',
            'unique_id': 'str',
            'meta_properties': 'str',
            'time_created': 'datetime'
        }

        self.attribute_map = {
            'log_group_id': 'logGroupId',
            'unique_id': 'uniqueId',
            'meta_properties': 'metaProperties',
            'time_created': 'timeCreated'
        }

        self._log_group_id = None
        self._unique_id = None
        self._meta_properties = None
        self._time_created = None

    @property
    def log_group_id(self):
        """
        **[Required]** Gets the log_group_id of this GenerateAgentObjectNameDetails.
        Log group OCID


        :return: The log_group_id of this GenerateAgentObjectNameDetails.
        :rtype: str
        """
        return self._log_group_id

    @log_group_id.setter
    def log_group_id(self, log_group_id):
        """
        Sets the log_group_id of this GenerateAgentObjectNameDetails.
        Log group OCID


        :param log_group_id: The log_group_id of this GenerateAgentObjectNameDetails.
        :type: str
        """
        self._log_group_id = log_group_id

    @property
    def unique_id(self):
        """
        **[Required]** Gets the unique_id of this GenerateAgentObjectNameDetails.
        Internal identifier used to uniquely identify the agent upload request


        :return: The unique_id of this GenerateAgentObjectNameDetails.
        :rtype: str
        """
        return self._unique_id

    @unique_id.setter
    def unique_id(self, unique_id):
        """
        Sets the unique_id of this GenerateAgentObjectNameDetails.
        Internal identifier used to uniquely identify the agent upload request


        :param unique_id: The unique_id of this GenerateAgentObjectNameDetails.
        :type: str
        """
        self._unique_id = unique_id

    @property
    def meta_properties(self):
        """
        **[Required]** Gets the meta_properties of this GenerateAgentObjectNameDetails.
        Metadata associated with the upload used during processing


        :return: The meta_properties of this GenerateAgentObjectNameDetails.
        :rtype: str
        """
        return self._meta_properties

    @meta_properties.setter
    def meta_properties(self, meta_properties):
        """
        Sets the meta_properties of this GenerateAgentObjectNameDetails.
        Metadata associated with the upload used during processing


        :param meta_properties: The meta_properties of this GenerateAgentObjectNameDetails.
        :type: str
        """
        self._meta_properties = meta_properties

    @property
    def time_created(self):
        """
        **[Required]** Gets the time_created of this GenerateAgentObjectNameDetails.
        The time when this upload is created. An RFC3339 formatted datetime string


        :return: The time_created of this GenerateAgentObjectNameDetails.
        :rtype: datetime
        """
        return self._time_created

    @time_created.setter
    def time_created(self, time_created):
        """
        Sets the time_created of this GenerateAgentObjectNameDetails.
        The time when this upload is created. An RFC3339 formatted datetime string


        :param time_created: The time_created of this GenerateAgentObjectNameDetails.
        :type: datetime
        """
        self._time_created = time_created

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
