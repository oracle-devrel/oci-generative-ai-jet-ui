# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class RequestSummarizedInstallationUsageDetails(object):
    """
    Parameters for filtering installations.
    """

    #: A constant which can be used with the sort_order property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "ASC"
    SORT_ORDER_ASC = "ASC"

    #: A constant which can be used with the sort_order property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "DESC"
    SORT_ORDER_DESC = "DESC"

    #: A constant which can be used with the sort_by property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "jreDistribution"
    SORT_BY_JRE_DISTRIBUTION = "jreDistribution"

    #: A constant which can be used with the sort_by property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "jreVendor"
    SORT_BY_JRE_VENDOR = "jreVendor"

    #: A constant which can be used with the sort_by property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "jreVersion"
    SORT_BY_JRE_VERSION = "jreVersion"

    #: A constant which can be used with the sort_by property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "path"
    SORT_BY_PATH = "path"

    #: A constant which can be used with the sort_by property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "timeFirstSeen"
    SORT_BY_TIME_FIRST_SEEN = "timeFirstSeen"

    #: A constant which can be used with the sort_by property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "timeLastSeen"
    SORT_BY_TIME_LAST_SEEN = "timeLastSeen"

    #: A constant which can be used with the sort_by property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "approximateApplicationCount"
    SORT_BY_APPROXIMATE_APPLICATION_COUNT = "approximateApplicationCount"

    #: A constant which can be used with the sort_by property of a RequestSummarizedInstallationUsageDetails.
    #: This constant has a value of "approximateManagedInstanceCount"
    SORT_BY_APPROXIMATE_MANAGED_INSTANCE_COUNT = "approximateManagedInstanceCount"

    def __init__(self, **kwargs):
        """
        Initializes a new RequestSummarizedInstallationUsageDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param time_start:
            The value to assign to the time_start property of this RequestSummarizedInstallationUsageDetails.
        :type time_start: datetime

        :param time_end:
            The value to assign to the time_end property of this RequestSummarizedInstallationUsageDetails.
        :type time_end: datetime

        :param installation_path:
            The value to assign to the installation_path property of this RequestSummarizedInstallationUsageDetails.
        :type installation_path: str

        :param jre_vendor:
            The value to assign to the jre_vendor property of this RequestSummarizedInstallationUsageDetails.
        :type jre_vendor: str

        :param jre_distribution:
            The value to assign to the jre_distribution property of this RequestSummarizedInstallationUsageDetails.
        :type jre_distribution: str

        :param jre_version:
            The value to assign to the jre_version property of this RequestSummarizedInstallationUsageDetails.
        :type jre_version: str

        :param application_id:
            The value to assign to the application_id property of this RequestSummarizedInstallationUsageDetails.
        :type application_id: str

        :param managed_instance_id:
            The value to assign to the managed_instance_id property of this RequestSummarizedInstallationUsageDetails.
        :type managed_instance_id: str

        :param sort_order:
            The value to assign to the sort_order property of this RequestSummarizedInstallationUsageDetails.
            Allowed values for this property are: "ASC", "DESC"
        :type sort_order: str

        :param sort_by:
            The value to assign to the sort_by property of this RequestSummarizedInstallationUsageDetails.
            Allowed values for this property are: "jreDistribution", "jreVendor", "jreVersion", "path", "timeFirstSeen", "timeLastSeen", "approximateApplicationCount", "approximateManagedInstanceCount"
        :type sort_by: str

        :param fields:
            The value to assign to the fields property of this RequestSummarizedInstallationUsageDetails.
        :type fields: list[oci.jms.models.SummarizeInstallationUsageFields]

        """
        self.swagger_types = {
            'time_start': 'datetime',
            'time_end': 'datetime',
            'installation_path': 'str',
            'jre_vendor': 'str',
            'jre_distribution': 'str',
            'jre_version': 'str',
            'application_id': 'str',
            'managed_instance_id': 'str',
            'sort_order': 'str',
            'sort_by': 'str',
            'fields': 'list[SummarizeInstallationUsageFields]'
        }

        self.attribute_map = {
            'time_start': 'timeStart',
            'time_end': 'timeEnd',
            'installation_path': 'installationPath',
            'jre_vendor': 'jreVendor',
            'jre_distribution': 'jreDistribution',
            'jre_version': 'jreVersion',
            'application_id': 'applicationId',
            'managed_instance_id': 'managedInstanceId',
            'sort_order': 'sortOrder',
            'sort_by': 'sortBy',
            'fields': 'fields'
        }

        self._time_start = None
        self._time_end = None
        self._installation_path = None
        self._jre_vendor = None
        self._jre_distribution = None
        self._jre_version = None
        self._application_id = None
        self._managed_instance_id = None
        self._sort_order = None
        self._sort_by = None
        self._fields = None

    @property
    def time_start(self):
        """
        Gets the time_start of this RequestSummarizedInstallationUsageDetails.
        The start of the time period during which resources are searched (formatted according to RFC3339). Defaults to current time minus seven days.


        :return: The time_start of this RequestSummarizedInstallationUsageDetails.
        :rtype: datetime
        """
        return self._time_start

    @time_start.setter
    def time_start(self, time_start):
        """
        Sets the time_start of this RequestSummarizedInstallationUsageDetails.
        The start of the time period during which resources are searched (formatted according to RFC3339). Defaults to current time minus seven days.


        :param time_start: The time_start of this RequestSummarizedInstallationUsageDetails.
        :type: datetime
        """
        self._time_start = time_start

    @property
    def time_end(self):
        """
        Gets the time_end of this RequestSummarizedInstallationUsageDetails.
        The end of the time period during which resources are searched (formatted according to RFC3339). Defaults to current time.


        :return: The time_end of this RequestSummarizedInstallationUsageDetails.
        :rtype: datetime
        """
        return self._time_end

    @time_end.setter
    def time_end(self, time_end):
        """
        Sets the time_end of this RequestSummarizedInstallationUsageDetails.
        The end of the time period during which resources are searched (formatted according to RFC3339). Defaults to current time.


        :param time_end: The time_end of this RequestSummarizedInstallationUsageDetails.
        :type: datetime
        """
        self._time_end = time_end

    @property
    def installation_path(self):
        """
        Gets the installation_path of this RequestSummarizedInstallationUsageDetails.
        The path of the installation.


        :return: The installation_path of this RequestSummarizedInstallationUsageDetails.
        :rtype: str
        """
        return self._installation_path

    @installation_path.setter
    def installation_path(self, installation_path):
        """
        Sets the installation_path of this RequestSummarizedInstallationUsageDetails.
        The path of the installation.


        :param installation_path: The installation_path of this RequestSummarizedInstallationUsageDetails.
        :type: str
        """
        self._installation_path = installation_path

    @property
    def jre_vendor(self):
        """
        Gets the jre_vendor of this RequestSummarizedInstallationUsageDetails.
        The vendor of the related Java Runtime.


        :return: The jre_vendor of this RequestSummarizedInstallationUsageDetails.
        :rtype: str
        """
        return self._jre_vendor

    @jre_vendor.setter
    def jre_vendor(self, jre_vendor):
        """
        Sets the jre_vendor of this RequestSummarizedInstallationUsageDetails.
        The vendor of the related Java Runtime.


        :param jre_vendor: The jre_vendor of this RequestSummarizedInstallationUsageDetails.
        :type: str
        """
        self._jre_vendor = jre_vendor

    @property
    def jre_distribution(self):
        """
        Gets the jre_distribution of this RequestSummarizedInstallationUsageDetails.
        The distribution of the related Java Runtime.


        :return: The jre_distribution of this RequestSummarizedInstallationUsageDetails.
        :rtype: str
        """
        return self._jre_distribution

    @jre_distribution.setter
    def jre_distribution(self, jre_distribution):
        """
        Sets the jre_distribution of this RequestSummarizedInstallationUsageDetails.
        The distribution of the related Java Runtime.


        :param jre_distribution: The jre_distribution of this RequestSummarizedInstallationUsageDetails.
        :type: str
        """
        self._jre_distribution = jre_distribution

    @property
    def jre_version(self):
        """
        Gets the jre_version of this RequestSummarizedInstallationUsageDetails.
        The version of the related Java Runtime.


        :return: The jre_version of this RequestSummarizedInstallationUsageDetails.
        :rtype: str
        """
        return self._jre_version

    @jre_version.setter
    def jre_version(self, jre_version):
        """
        Sets the jre_version of this RequestSummarizedInstallationUsageDetails.
        The version of the related Java Runtime.


        :param jre_version: The jre_version of this RequestSummarizedInstallationUsageDetails.
        :type: str
        """
        self._jre_version = jre_version

    @property
    def application_id(self):
        """
        Gets the application_id of this RequestSummarizedInstallationUsageDetails.
        The ID of the related application.


        :return: The application_id of this RequestSummarizedInstallationUsageDetails.
        :rtype: str
        """
        return self._application_id

    @application_id.setter
    def application_id(self, application_id):
        """
        Sets the application_id of this RequestSummarizedInstallationUsageDetails.
        The ID of the related application.


        :param application_id: The application_id of this RequestSummarizedInstallationUsageDetails.
        :type: str
        """
        self._application_id = application_id

    @property
    def managed_instance_id(self):
        """
        Gets the managed_instance_id of this RequestSummarizedInstallationUsageDetails.
        The ID of the related managed instance.


        :return: The managed_instance_id of this RequestSummarizedInstallationUsageDetails.
        :rtype: str
        """
        return self._managed_instance_id

    @managed_instance_id.setter
    def managed_instance_id(self, managed_instance_id):
        """
        Sets the managed_instance_id of this RequestSummarizedInstallationUsageDetails.
        The ID of the related managed instance.


        :param managed_instance_id: The managed_instance_id of this RequestSummarizedInstallationUsageDetails.
        :type: str
        """
        self._managed_instance_id = managed_instance_id

    @property
    def sort_order(self):
        """
        Gets the sort_order of this RequestSummarizedInstallationUsageDetails.
        The sort order to use, either 'asc' or 'desc'.

        Allowed values for this property are: "ASC", "DESC"


        :return: The sort_order of this RequestSummarizedInstallationUsageDetails.
        :rtype: str
        """
        return self._sort_order

    @sort_order.setter
    def sort_order(self, sort_order):
        """
        Sets the sort_order of this RequestSummarizedInstallationUsageDetails.
        The sort order to use, either 'asc' or 'desc'.


        :param sort_order: The sort_order of this RequestSummarizedInstallationUsageDetails.
        :type: str
        """
        allowed_values = ["ASC", "DESC"]
        if not value_allowed_none_or_none_sentinel(sort_order, allowed_values):
            raise ValueError(
                "Invalid value for `sort_order`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._sort_order = sort_order

    @property
    def sort_by(self):
        """
        Gets the sort_by of this RequestSummarizedInstallationUsageDetails.
        The field to sort installation views. Only one sort order may be provided.
        Default order for _timeFirstSeen_, _timeLastSeen_, _jreVersion_, _approximateApplicationCount_
        and _approximateManagedInstanceCount_  is **descending**.
        Default order for _jreDistribution_ and _jreVendor_ is **ascending**. If no value is specified _timeLastSeen_ is default.

        Allowed values for this property are: "jreDistribution", "jreVendor", "jreVersion", "path", "timeFirstSeen", "timeLastSeen", "approximateApplicationCount", "approximateManagedInstanceCount"


        :return: The sort_by of this RequestSummarizedInstallationUsageDetails.
        :rtype: str
        """
        return self._sort_by

    @sort_by.setter
    def sort_by(self, sort_by):
        """
        Sets the sort_by of this RequestSummarizedInstallationUsageDetails.
        The field to sort installation views. Only one sort order may be provided.
        Default order for _timeFirstSeen_, _timeLastSeen_, _jreVersion_, _approximateApplicationCount_
        and _approximateManagedInstanceCount_  is **descending**.
        Default order for _jreDistribution_ and _jreVendor_ is **ascending**. If no value is specified _timeLastSeen_ is default.


        :param sort_by: The sort_by of this RequestSummarizedInstallationUsageDetails.
        :type: str
        """
        allowed_values = ["jreDistribution", "jreVendor", "jreVersion", "path", "timeFirstSeen", "timeLastSeen", "approximateApplicationCount", "approximateManagedInstanceCount"]
        if not value_allowed_none_or_none_sentinel(sort_by, allowed_values):
            raise ValueError(
                "Invalid value for `sort_by`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._sort_by = sort_by

    @property
    def fields(self):
        """
        Gets the fields of this RequestSummarizedInstallationUsageDetails.
        Additional fields to include into the returned model on top of the required ones.
        This parameter can also include 'approximateApplicationCount' and 'approximateManagedInstanceCount'.
        For example 'approximateApplicationCount,approximateManagedInstanceCount'.


        :return: The fields of this RequestSummarizedInstallationUsageDetails.
        :rtype: list[oci.jms.models.SummarizeInstallationUsageFields]
        """
        return self._fields

    @fields.setter
    def fields(self, fields):
        """
        Sets the fields of this RequestSummarizedInstallationUsageDetails.
        Additional fields to include into the returned model on top of the required ones.
        This parameter can also include 'approximateApplicationCount' and 'approximateManagedInstanceCount'.
        For example 'approximateApplicationCount,approximateManagedInstanceCount'.


        :param fields: The fields of this RequestSummarizedInstallationUsageDetails.
        :type: list[oci.jms.models.SummarizeInstallationUsageFields]
        """
        self._fields = fields

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
