# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class SavedScheduleReport(object):
    """
    notification to customer.
    """

    #: A constant which can be used with the notification_type property of a SavedScheduleReport.
    #: This constant has a value of "EMAIL"
    NOTIFICATION_TYPE_EMAIL = "EMAIL"

    def __init__(self, **kwargs):
        """
        Initializes a new SavedScheduleReport object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param display_name:
            The value to assign to the display_name property of this SavedScheduleReport.
        :type display_name: str

        :param notification_type:
            The value to assign to the notification_type property of this SavedScheduleReport.
            Allowed values for this property are: "EMAIL"
        :type notification_type: str

        :param notification_target:
            The value to assign to the notification_target property of this SavedScheduleReport.
        :type notification_target: str

        """
        self.swagger_types = {
            'display_name': 'str',
            'notification_type': 'str',
            'notification_target': 'str'
        }

        self.attribute_map = {
            'display_name': 'displayName',
            'notification_type': 'notificationType',
            'notification_target': 'notificationTarget'
        }

        self._display_name = None
        self._notification_type = None
        self._notification_target = None

    @property
    def display_name(self):
        """
        **[Required]** Gets the display_name of this SavedScheduleReport.
        the name of notification


        :return: The display_name of this SavedScheduleReport.
        :rtype: str
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        """
        Sets the display_name of this SavedScheduleReport.
        the name of notification


        :param display_name: The display_name of this SavedScheduleReport.
        :type: str
        """
        self._display_name = display_name

    @property
    def notification_type(self):
        """
        Gets the notification_type of this SavedScheduleReport.
        notification type, eg EMAIL.

        Allowed values for this property are: "EMAIL"


        :return: The notification_type of this SavedScheduleReport.
        :rtype: str
        """
        return self._notification_type

    @notification_type.setter
    def notification_type(self, notification_type):
        """
        Sets the notification_type of this SavedScheduleReport.
        notification type, eg EMAIL.


        :param notification_type: The notification_type of this SavedScheduleReport.
        :type: str
        """
        allowed_values = ["EMAIL"]
        if not value_allowed_none_or_none_sentinel(notification_type, allowed_values):
            raise ValueError(
                "Invalid value for `notification_type`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._notification_type = notification_type

    @property
    def notification_target(self):
        """
        Gets the notification_target of this SavedScheduleReport.
        notification destination.


        :return: The notification_target of this SavedScheduleReport.
        :rtype: str
        """
        return self._notification_target

    @notification_target.setter
    def notification_target(self, notification_target):
        """
        Sets the notification_target of this SavedScheduleReport.
        notification destination.


        :param notification_target: The notification_target of this SavedScheduleReport.
        :type: str
        """
        self._notification_target = notification_target

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
