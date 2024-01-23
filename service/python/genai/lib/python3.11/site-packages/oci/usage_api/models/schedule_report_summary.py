# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class ScheduleReportSummary(object):
    """
    Schedule report in list request.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new ScheduleReportSummary object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param id:
            The value to assign to the id property of this ScheduleReportSummary.
        :type id: str

        :param saved_schedule_report:
            The value to assign to the saved_schedule_report property of this ScheduleReportSummary.
        :type saved_schedule_report: oci.usage_api.models.SavedScheduleReport

        """
        self.swagger_types = {
            'id': 'str',
            'saved_schedule_report': 'SavedScheduleReport'
        }

        self.attribute_map = {
            'id': 'id',
            'saved_schedule_report': 'savedScheduleReport'
        }

        self._id = None
        self._saved_schedule_report = None

    @property
    def id(self):
        """
        **[Required]** Gets the id of this ScheduleReportSummary.
        The Schedule report OCID.


        :return: The id of this ScheduleReportSummary.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id):
        """
        Sets the id of this ScheduleReportSummary.
        The Schedule report OCID.


        :param id: The id of this ScheduleReportSummary.
        :type: str
        """
        self._id = id

    @property
    def saved_schedule_report(self):
        """
        Gets the saved_schedule_report of this ScheduleReportSummary.

        :return: The saved_schedule_report of this ScheduleReportSummary.
        :rtype: oci.usage_api.models.SavedScheduleReport
        """
        return self._saved_schedule_report

    @saved_schedule_report.setter
    def saved_schedule_report(self, saved_schedule_report):
        """
        Sets the saved_schedule_report of this ScheduleReportSummary.

        :param saved_schedule_report: The saved_schedule_report of this ScheduleReportSummary.
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
