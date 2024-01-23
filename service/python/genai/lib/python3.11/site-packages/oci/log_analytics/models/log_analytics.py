# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class LogAnalytics(object):
    """
    Description of LogAnalytics.
    """

    #: A constant which can be used with the lifecycle_state property of a LogAnalytics.
    #: This constant has a value of "ACTIVE"
    LIFECYCLE_STATE_ACTIVE = "ACTIVE"

    #: A constant which can be used with the lifecycle_state property of a LogAnalytics.
    #: This constant has a value of "DELETED"
    LIFECYCLE_STATE_DELETED = "DELETED"

    def __init__(self, **kwargs):
        """
        Initializes a new LogAnalytics object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param id:
            The value to assign to the id property of this LogAnalytics.
        :type id: str

        :param display_name:
            The value to assign to the display_name property of this LogAnalytics.
        :type display_name: str

        :param compartment_id:
            The value to assign to the compartment_id property of this LogAnalytics.
        :type compartment_id: str

        :param log_analytics_type:
            The value to assign to the log_analytics_type property of this LogAnalytics.
        :type log_analytics_type: str

        :param time_created:
            The value to assign to the time_created property of this LogAnalytics.
        :type time_created: datetime

        :param time_updated:
            The value to assign to the time_updated property of this LogAnalytics.
        :type time_updated: datetime

        :param lifecycle_state:
            The value to assign to the lifecycle_state property of this LogAnalytics.
            Allowed values for this property are: "ACTIVE", "DELETED"
        :type lifecycle_state: str

        :param lifecyle_details:
            The value to assign to the lifecyle_details property of this LogAnalytics.
        :type lifecyle_details: str

        :param freeform_tags:
            The value to assign to the freeform_tags property of this LogAnalytics.
        :type freeform_tags: dict(str, str)

        :param defined_tags:
            The value to assign to the defined_tags property of this LogAnalytics.
        :type defined_tags: dict(str, dict(str, object))

        """
        self.swagger_types = {
            'id': 'str',
            'display_name': 'str',
            'compartment_id': 'str',
            'log_analytics_type': 'str',
            'time_created': 'datetime',
            'time_updated': 'datetime',
            'lifecycle_state': 'str',
            'lifecyle_details': 'str',
            'freeform_tags': 'dict(str, str)',
            'defined_tags': 'dict(str, dict(str, object))'
        }

        self.attribute_map = {
            'id': 'id',
            'display_name': 'displayName',
            'compartment_id': 'compartmentId',
            'log_analytics_type': 'logAnalyticsType',
            'time_created': 'timeCreated',
            'time_updated': 'timeUpdated',
            'lifecycle_state': 'lifecycleState',
            'lifecyle_details': 'lifecyleDetails',
            'freeform_tags': 'freeformTags',
            'defined_tags': 'definedTags'
        }

        self._id = None
        self._display_name = None
        self._compartment_id = None
        self._log_analytics_type = None
        self._time_created = None
        self._time_updated = None
        self._lifecycle_state = None
        self._lifecyle_details = None
        self._freeform_tags = None
        self._defined_tags = None

    @property
    def id(self):
        """
        **[Required]** Gets the id of this LogAnalytics.
        Unique identifier that is immutable on creation


        :return: The id of this LogAnalytics.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id):
        """
        Sets the id of this LogAnalytics.
        Unique identifier that is immutable on creation


        :param id: The id of this LogAnalytics.
        :type: str
        """
        self._id = id

    @property
    def display_name(self):
        """
        Gets the display_name of this LogAnalytics.
        LogAnalytics Identifier, can be renamed


        :return: The display_name of this LogAnalytics.
        :rtype: str
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        """
        Sets the display_name of this LogAnalytics.
        LogAnalytics Identifier, can be renamed


        :param display_name: The display_name of this LogAnalytics.
        :type: str
        """
        self._display_name = display_name

    @property
    def compartment_id(self):
        """
        **[Required]** Gets the compartment_id of this LogAnalytics.
        Compartment Identifier


        :return: The compartment_id of this LogAnalytics.
        :rtype: str
        """
        return self._compartment_id

    @compartment_id.setter
    def compartment_id(self, compartment_id):
        """
        Sets the compartment_id of this LogAnalytics.
        Compartment Identifier


        :param compartment_id: The compartment_id of this LogAnalytics.
        :type: str
        """
        self._compartment_id = compartment_id

    @property
    def log_analytics_type(self):
        """
        **[Required]** Gets the log_analytics_type of this LogAnalytics.
        Type of the LogAnalytics.


        :return: The log_analytics_type of this LogAnalytics.
        :rtype: str
        """
        return self._log_analytics_type

    @log_analytics_type.setter
    def log_analytics_type(self, log_analytics_type):
        """
        Sets the log_analytics_type of this LogAnalytics.
        Type of the LogAnalytics.


        :param log_analytics_type: The log_analytics_type of this LogAnalytics.
        :type: str
        """
        self._log_analytics_type = log_analytics_type

    @property
    def time_created(self):
        """
        Gets the time_created of this LogAnalytics.
        The time the the LogAnalytics was created. An RFC3339 formatted datetime string


        :return: The time_created of this LogAnalytics.
        :rtype: datetime
        """
        return self._time_created

    @time_created.setter
    def time_created(self, time_created):
        """
        Sets the time_created of this LogAnalytics.
        The time the the LogAnalytics was created. An RFC3339 formatted datetime string


        :param time_created: The time_created of this LogAnalytics.
        :type: datetime
        """
        self._time_created = time_created

    @property
    def time_updated(self):
        """
        Gets the time_updated of this LogAnalytics.
        The time the LogAnalytics was updated. An RFC3339 formatted datetime string


        :return: The time_updated of this LogAnalytics.
        :rtype: datetime
        """
        return self._time_updated

    @time_updated.setter
    def time_updated(self, time_updated):
        """
        Sets the time_updated of this LogAnalytics.
        The time the LogAnalytics was updated. An RFC3339 formatted datetime string


        :param time_updated: The time_updated of this LogAnalytics.
        :type: datetime
        """
        self._time_updated = time_updated

    @property
    def lifecycle_state(self):
        """
        Gets the lifecycle_state of this LogAnalytics.
        The current state of the LogAnalytics.

        Allowed values for this property are: "ACTIVE", "DELETED"


        :return: The lifecycle_state of this LogAnalytics.
        :rtype: str
        """
        return self._lifecycle_state

    @lifecycle_state.setter
    def lifecycle_state(self, lifecycle_state):
        """
        Sets the lifecycle_state of this LogAnalytics.
        The current state of the LogAnalytics.


        :param lifecycle_state: The lifecycle_state of this LogAnalytics.
        :type: str
        """
        allowed_values = ["ACTIVE", "DELETED"]
        if not value_allowed_none_or_none_sentinel(lifecycle_state, allowed_values):
            raise ValueError(
                "Invalid value for `lifecycle_state`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._lifecycle_state = lifecycle_state

    @property
    def lifecyle_details(self):
        """
        Gets the lifecyle_details of this LogAnalytics.
        A message describing the current state in more detail. For example, can be used to provide actionable information for a resource in Failed state.


        :return: The lifecyle_details of this LogAnalytics.
        :rtype: str
        """
        return self._lifecyle_details

    @lifecyle_details.setter
    def lifecyle_details(self, lifecyle_details):
        """
        Sets the lifecyle_details of this LogAnalytics.
        A message describing the current state in more detail. For example, can be used to provide actionable information for a resource in Failed state.


        :param lifecyle_details: The lifecyle_details of this LogAnalytics.
        :type: str
        """
        self._lifecyle_details = lifecyle_details

    @property
    def freeform_tags(self):
        """
        Gets the freeform_tags of this LogAnalytics.
        Simple key-value pair that is applied without any predefined name, type or scope. Exists for cross-compatibility only.
        Example: `{\"bar-key\": \"value\"}`


        :return: The freeform_tags of this LogAnalytics.
        :rtype: dict(str, str)
        """
        return self._freeform_tags

    @freeform_tags.setter
    def freeform_tags(self, freeform_tags):
        """
        Sets the freeform_tags of this LogAnalytics.
        Simple key-value pair that is applied without any predefined name, type or scope. Exists for cross-compatibility only.
        Example: `{\"bar-key\": \"value\"}`


        :param freeform_tags: The freeform_tags of this LogAnalytics.
        :type: dict(str, str)
        """
        self._freeform_tags = freeform_tags

    @property
    def defined_tags(self):
        """
        Gets the defined_tags of this LogAnalytics.
        Defined tags for this resource. Each key is predefined and scoped to a namespace.
        Example: `{\"foo-namespace\": {\"bar-key\": \"value\"}}`


        :return: The defined_tags of this LogAnalytics.
        :rtype: dict(str, dict(str, object))
        """
        return self._defined_tags

    @defined_tags.setter
    def defined_tags(self, defined_tags):
        """
        Sets the defined_tags of this LogAnalytics.
        Defined tags for this resource. Each key is predefined and scoped to a namespace.
        Example: `{\"foo-namespace\": {\"bar-key\": \"value\"}}`


        :param defined_tags: The defined_tags of this LogAnalytics.
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
