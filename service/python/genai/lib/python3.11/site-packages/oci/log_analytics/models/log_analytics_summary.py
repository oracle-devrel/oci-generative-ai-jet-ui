# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class LogAnalyticsSummary(object):
    """
    Summary of the LogAnalytics.
    """

    #: A constant which can be used with the lifecycle_state property of a LogAnalyticsSummary.
    #: This constant has a value of "ACTIVE"
    LIFECYCLE_STATE_ACTIVE = "ACTIVE"

    #: A constant which can be used with the lifecycle_state property of a LogAnalyticsSummary.
    #: This constant has a value of "DELETED"
    LIFECYCLE_STATE_DELETED = "DELETED"

    def __init__(self, **kwargs):
        """
        Initializes a new LogAnalyticsSummary object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param id:
            The value to assign to the id property of this LogAnalyticsSummary.
        :type id: str

        :param display_name:
            The value to assign to the display_name property of this LogAnalyticsSummary.
        :type display_name: str

        :param compartment_id:
            The value to assign to the compartment_id property of this LogAnalyticsSummary.
        :type compartment_id: str

        :param log_analytics_type:
            The value to assign to the log_analytics_type property of this LogAnalyticsSummary.
        :type log_analytics_type: str

        :param time_created:
            The value to assign to the time_created property of this LogAnalyticsSummary.
        :type time_created: datetime

        :param time_updated:
            The value to assign to the time_updated property of this LogAnalyticsSummary.
        :type time_updated: datetime

        :param lifecycle_state:
            The value to assign to the lifecycle_state property of this LogAnalyticsSummary.
            Allowed values for this property are: "ACTIVE", "DELETED"
        :type lifecycle_state: str

        :param lifecycle_details:
            The value to assign to the lifecycle_details property of this LogAnalyticsSummary.
        :type lifecycle_details: str

        """
        self.swagger_types = {
            'id': 'str',
            'display_name': 'str',
            'compartment_id': 'str',
            'log_analytics_type': 'str',
            'time_created': 'datetime',
            'time_updated': 'datetime',
            'lifecycle_state': 'str',
            'lifecycle_details': 'str'
        }

        self.attribute_map = {
            'id': 'id',
            'display_name': 'displayName',
            'compartment_id': 'compartmentId',
            'log_analytics_type': 'logAnalyticsType',
            'time_created': 'timeCreated',
            'time_updated': 'timeUpdated',
            'lifecycle_state': 'lifecycleState',
            'lifecycle_details': 'lifecycleDetails'
        }

        self._id = None
        self._display_name = None
        self._compartment_id = None
        self._log_analytics_type = None
        self._time_created = None
        self._time_updated = None
        self._lifecycle_state = None
        self._lifecycle_details = None

    @property
    def id(self):
        """
        **[Required]** Gets the id of this LogAnalyticsSummary.
        Unique identifier that is immutable on creation


        :return: The id of this LogAnalyticsSummary.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id):
        """
        Sets the id of this LogAnalyticsSummary.
        Unique identifier that is immutable on creation


        :param id: The id of this LogAnalyticsSummary.
        :type: str
        """
        self._id = id

    @property
    def display_name(self):
        """
        Gets the display_name of this LogAnalyticsSummary.
        LogAnalytics Identifier, can be renamed


        :return: The display_name of this LogAnalyticsSummary.
        :rtype: str
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        """
        Sets the display_name of this LogAnalyticsSummary.
        LogAnalytics Identifier, can be renamed


        :param display_name: The display_name of this LogAnalyticsSummary.
        :type: str
        """
        self._display_name = display_name

    @property
    def compartment_id(self):
        """
        **[Required]** Gets the compartment_id of this LogAnalyticsSummary.
        Compartment Identifier


        :return: The compartment_id of this LogAnalyticsSummary.
        :rtype: str
        """
        return self._compartment_id

    @compartment_id.setter
    def compartment_id(self, compartment_id):
        """
        Sets the compartment_id of this LogAnalyticsSummary.
        Compartment Identifier


        :param compartment_id: The compartment_id of this LogAnalyticsSummary.
        :type: str
        """
        self._compartment_id = compartment_id

    @property
    def log_analytics_type(self):
        """
        **[Required]** Gets the log_analytics_type of this LogAnalyticsSummary.
        Type of the LogAnalytics.


        :return: The log_analytics_type of this LogAnalyticsSummary.
        :rtype: str
        """
        return self._log_analytics_type

    @log_analytics_type.setter
    def log_analytics_type(self, log_analytics_type):
        """
        Sets the log_analytics_type of this LogAnalyticsSummary.
        Type of the LogAnalytics.


        :param log_analytics_type: The log_analytics_type of this LogAnalyticsSummary.
        :type: str
        """
        self._log_analytics_type = log_analytics_type

    @property
    def time_created(self):
        """
        Gets the time_created of this LogAnalyticsSummary.
        The time the the LogAnalytics was created. An RFC3339 formatted datetime string


        :return: The time_created of this LogAnalyticsSummary.
        :rtype: datetime
        """
        return self._time_created

    @time_created.setter
    def time_created(self, time_created):
        """
        Sets the time_created of this LogAnalyticsSummary.
        The time the the LogAnalytics was created. An RFC3339 formatted datetime string


        :param time_created: The time_created of this LogAnalyticsSummary.
        :type: datetime
        """
        self._time_created = time_created

    @property
    def time_updated(self):
        """
        Gets the time_updated of this LogAnalyticsSummary.
        The time the LogAnalytics was updated. An RFC3339 formatted datetime string


        :return: The time_updated of this LogAnalyticsSummary.
        :rtype: datetime
        """
        return self._time_updated

    @time_updated.setter
    def time_updated(self, time_updated):
        """
        Sets the time_updated of this LogAnalyticsSummary.
        The time the LogAnalytics was updated. An RFC3339 formatted datetime string


        :param time_updated: The time_updated of this LogAnalyticsSummary.
        :type: datetime
        """
        self._time_updated = time_updated

    @property
    def lifecycle_state(self):
        """
        Gets the lifecycle_state of this LogAnalyticsSummary.
        The current state of the LogAnalytics.

        Allowed values for this property are: "ACTIVE", "DELETED"


        :return: The lifecycle_state of this LogAnalyticsSummary.
        :rtype: str
        """
        return self._lifecycle_state

    @lifecycle_state.setter
    def lifecycle_state(self, lifecycle_state):
        """
        Sets the lifecycle_state of this LogAnalyticsSummary.
        The current state of the LogAnalytics.


        :param lifecycle_state: The lifecycle_state of this LogAnalyticsSummary.
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
    def lifecycle_details(self):
        """
        Gets the lifecycle_details of this LogAnalyticsSummary.
        A message describing the current state in more detail. For example, can be used to provide actionable information for a resource in Failed state.


        :return: The lifecycle_details of this LogAnalyticsSummary.
        :rtype: str
        """
        return self._lifecycle_details

    @lifecycle_details.setter
    def lifecycle_details(self, lifecycle_details):
        """
        Sets the lifecycle_details of this LogAnalyticsSummary.
        A message describing the current state in more detail. For example, can be used to provide actionable information for a resource in Failed state.


        :param lifecycle_details: The lifecycle_details of this LogAnalyticsSummary.
        :type: str
        """
        self._lifecycle_details = lifecycle_details

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
