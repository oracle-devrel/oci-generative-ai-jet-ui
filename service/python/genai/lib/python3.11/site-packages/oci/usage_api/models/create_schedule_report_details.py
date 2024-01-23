# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class CreateScheduleReportDetails(object):
    """
    New custom table detail.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new CreateScheduleReportDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param compartment_id:
            The value to assign to the compartment_id property of this CreateScheduleReportDetails.
        :type compartment_id: str

        :param query_id:
            The value to assign to the query_id property of this CreateScheduleReportDetails.
        :type query_id: str

        :param saved_schedule_report:
            The value to assign to the saved_schedule_report property of this CreateScheduleReportDetails.
        :type saved_schedule_report: oci.usage_api.models.SavedScheduleReport

        """
        self.swagger_types = {
            'compartment_id': 'str',
            'query_id': 'str',
            'saved_schedule_report': 'SavedScheduleReport'
        }

        self.attribute_map = {
            'compartment_id': 'compartmentId',
            'query_id': 'queryId',
            'saved_schedule_report': 'savedScheduleReport'
        }

        self._compartment_id = None
        self._query_id = None
        self._saved_schedule_report = None

    @property
    def compartment_id(self):
        """
        **[Required]** Gets the compartment_id of this CreateScheduleReportDetails.
        The compartment OCID.


        :return: The compartment_id of this CreateScheduleReportDetails.
        :rtype: str
        """
        return self._compartment_id

    @compartment_id.setter
    def compartment_id(self, compartment_id):
        """
        Sets the compartment_id of this CreateScheduleReportDetails.
        The compartment OCID.


        :param compartment_id: The compartment_id of this CreateScheduleReportDetails.
        :type: str
        """
        self._compartment_id = compartment_id

    @property
    def query_id(self):
        """
        **[Required]** Gets the query_id of this CreateScheduleReportDetails.
        The query OCID.


        :return: The query_id of this CreateScheduleReportDetails.
        :rtype: str
        """
        return self._query_id

    @query_id.setter
    def query_id(self, query_id):
        """
        Sets the query_id of this CreateScheduleReportDetails.
        The query OCID.


        :param query_id: The query_id of this CreateScheduleReportDetails.
        :type: str
        """
        self._query_id = query_id

    @property
    def saved_schedule_report(self):
        """
        Gets the saved_schedule_report of this CreateScheduleReportDetails.

        :return: The saved_schedule_report of this CreateScheduleReportDetails.
        :rtype: oci.usage_api.models.SavedScheduleReport
        """
        return self._saved_schedule_report

    @saved_schedule_report.setter
    def saved_schedule_report(self, saved_schedule_report):
        """
        Sets the saved_schedule_report of this CreateScheduleReportDetails.

        :param saved_schedule_report: The saved_schedule_report of this CreateScheduleReportDetails.
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
