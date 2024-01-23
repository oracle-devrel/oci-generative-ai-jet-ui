# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class FawAdminInfoDetails(object):
    """
    Admin information to provision Analytics Warehouse Service.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new FawAdminInfoDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param adw_admin_pass:
            The value to assign to the adw_admin_pass property of this FawAdminInfoDetails.
        :type adw_admin_pass: str

        :param faw_service_pass:
            The value to assign to the faw_service_pass property of this FawAdminInfoDetails.
        :type faw_service_pass: str

        :param notification_email:
            The value to assign to the notification_email property of this FawAdminInfoDetails.
        :type notification_email: str

        """
        self.swagger_types = {
            'adw_admin_pass': 'str',
            'faw_service_pass': 'str',
            'notification_email': 'str'
        }

        self.attribute_map = {
            'adw_admin_pass': 'adwAdminPass',
            'faw_service_pass': 'fawServicePass',
            'notification_email': 'notificationEmail'
        }

        self._adw_admin_pass = None
        self._faw_service_pass = None
        self._notification_email = None

    @property
    def adw_admin_pass(self):
        """
        **[Required]** Gets the adw_admin_pass of this FawAdminInfoDetails.
        Password for the ADW to be created in User Tenancy


        :return: The adw_admin_pass of this FawAdminInfoDetails.
        :rtype: str
        """
        return self._adw_admin_pass

    @adw_admin_pass.setter
    def adw_admin_pass(self, adw_admin_pass):
        """
        Sets the adw_admin_pass of this FawAdminInfoDetails.
        Password for the ADW to be created in User Tenancy


        :param adw_admin_pass: The adw_admin_pass of this FawAdminInfoDetails.
        :type: str
        """
        self._adw_admin_pass = adw_admin_pass

    @property
    def faw_service_pass(self):
        """
        Gets the faw_service_pass of this FawAdminInfoDetails.
        Password for the auto-created FAWService user


        :return: The faw_service_pass of this FawAdminInfoDetails.
        :rtype: str
        """
        return self._faw_service_pass

    @faw_service_pass.setter
    def faw_service_pass(self, faw_service_pass):
        """
        Sets the faw_service_pass of this FawAdminInfoDetails.
        Password for the auto-created FAWService user


        :param faw_service_pass: The faw_service_pass of this FawAdminInfoDetails.
        :type: str
        """
        self._faw_service_pass = faw_service_pass

    @property
    def notification_email(self):
        """
        **[Required]** Gets the notification_email of this FawAdminInfoDetails.
        Email ID to send notification for Analytics Warehouse updates.


        :return: The notification_email of this FawAdminInfoDetails.
        :rtype: str
        """
        return self._notification_email

    @notification_email.setter
    def notification_email(self, notification_email):
        """
        Sets the notification_email of this FawAdminInfoDetails.
        Email ID to send notification for Analytics Warehouse updates.


        :param notification_email: The notification_email of this FawAdminInfoDetails.
        :type: str
        """
        self._notification_email = notification_email

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
