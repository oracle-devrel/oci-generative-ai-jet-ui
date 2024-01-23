# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class LogIncludedSearchSummary(object):
    """
    A summary of what the OCI included search does.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new LogIncludedSearchSummary object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param id:
            The value to assign to the id property of this LogIncludedSearchSummary.
        :type id: str

        :param display_name:
            The value to assign to the display_name property of this LogIncludedSearchSummary.
        :type display_name: str

        :param time_created:
            The value to assign to the time_created property of this LogIncludedSearchSummary.
        :type time_created: datetime

        :param time_last_modified:
            The value to assign to the time_last_modified property of this LogIncludedSearchSummary.
        :type time_last_modified: datetime

        """
        self.swagger_types = {
            'id': 'str',
            'display_name': 'str',
            'time_created': 'datetime',
            'time_last_modified': 'datetime'
        }

        self.attribute_map = {
            'id': 'id',
            'display_name': 'displayName',
            'time_created': 'timeCreated',
            'time_last_modified': 'timeLastModified'
        }

        self._id = None
        self._display_name = None
        self._time_created = None
        self._time_last_modified = None

    @property
    def id(self):
        """
        **[Required]** Gets the id of this LogIncludedSearchSummary.
        The OCID of the resource.


        :return: The id of this LogIncludedSearchSummary.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id):
        """
        Sets the id of this LogIncludedSearchSummary.
        The OCID of the resource.


        :param id: The id of this LogIncludedSearchSummary.
        :type: str
        """
        self._id = id

    @property
    def display_name(self):
        """
        **[Required]** Gets the display_name of this LogIncludedSearchSummary.
        The user-friendly display name. This must be unique within the enclosing resource,
        and it's changeable. Avoid entering confidential information.


        :return: The display_name of this LogIncludedSearchSummary.
        :rtype: str
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        """
        Sets the display_name of this LogIncludedSearchSummary.
        The user-friendly display name. This must be unique within the enclosing resource,
        and it's changeable. Avoid entering confidential information.


        :param display_name: The display_name of this LogIncludedSearchSummary.
        :type: str
        """
        self._display_name = display_name

    @property
    def time_created(self):
        """
        Gets the time_created of this LogIncludedSearchSummary.
        Time the resource was created.


        :return: The time_created of this LogIncludedSearchSummary.
        :rtype: datetime
        """
        return self._time_created

    @time_created.setter
    def time_created(self, time_created):
        """
        Sets the time_created of this LogIncludedSearchSummary.
        Time the resource was created.


        :param time_created: The time_created of this LogIncludedSearchSummary.
        :type: datetime
        """
        self._time_created = time_created

    @property
    def time_last_modified(self):
        """
        Gets the time_last_modified of this LogIncludedSearchSummary.
        Time the resource was last modified.


        :return: The time_last_modified of this LogIncludedSearchSummary.
        :rtype: datetime
        """
        return self._time_last_modified

    @time_last_modified.setter
    def time_last_modified(self, time_last_modified):
        """
        Sets the time_last_modified of this LogIncludedSearchSummary.
        Time the resource was last modified.


        :param time_last_modified: The time_last_modified of this LogIncludedSearchSummary.
        :type: datetime
        """
        self._time_last_modified = time_last_modified

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
