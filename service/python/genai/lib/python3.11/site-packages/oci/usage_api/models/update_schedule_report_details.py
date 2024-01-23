# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class UpdateScheduleReportDetails(object):
    """
    Details for updating schedule report.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new UpdateScheduleReportDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param saved_schedule_report:
            The value to assign to the saved_schedule_report property of this UpdateScheduleReportDetails.
        :type saved_schedule_report: oci.usage_api.models.SavedScheduleReport

        """
        self.swagger_types = {
            'saved_schedule_report': 'SavedScheduleReport'
        }

        self.attribute_map = {
            'saved_schedule_report': 'savedScheduleReport'
        }

        self._saved_schedule_report = None

    @property
    def saved_schedule_report(self):
        """
        **[Required]** Gets the saved_schedule_report of this UpdateScheduleReportDetails.

        :return: The saved_schedule_report of this UpdateScheduleReportDetails.
        :rtype: oci.usage_api.models.SavedScheduleReport
        """
        return self._saved_schedule_report

    @saved_schedule_report.setter
    def saved_schedule_report(self, saved_schedule_report):
        """
        Sets the saved_schedule_report of this UpdateScheduleReportDetails.

        :param saved_schedule_report: The saved_schedule_report of this UpdateScheduleReportDetails.
        :type: oci.usage_api.models.SavedScheduleReport
        """
        self._saved_schedule_report = saved_schedule_report

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
