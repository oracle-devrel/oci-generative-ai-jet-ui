# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class LogIncludedSearch(object):
    """
    A search provided by OCI that serves common customer needs.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new LogIncludedSearch object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param id:
            The value to assign to the id property of this LogIncludedSearch.
        :type id: str

        :param display_name:
            The value to assign to the display_name property of this LogIncludedSearch.
        :type display_name: str

        :param time_created:
            The value to assign to the time_created property of this LogIncludedSearch.
        :type time_created: datetime

        :param time_last_modified:
            The value to assign to the time_last_modified property of this LogIncludedSearch.
        :type time_last_modified: datetime

        :param description:
            The value to assign to the description property of this LogIncludedSearch.
        :type description: str

        :param query:
            The value to assign to the query property of this LogIncludedSearch.
        :type query: str

        :param defined_tags:
            The value to assign to the defined_tags property of this LogIncludedSearch.
        :type defined_tags: dict(str, dict(str, object))

        :param freeform_tags:
            The value to assign to the freeform_tags property of this LogIncludedSearch.
        :type freeform_tags: dict(str, str)

        """
        self.swagger_types = {
            'id': 'str',
            'display_name': 'str',
            'time_created': 'datetime',
            'time_last_modified': 'datetime',
            'description': 'str',
            'query': 'str',
            'defined_tags': 'dict(str, dict(str, object))',
            'freeform_tags': 'dict(str, str)'
        }

        self.attribute_map = {
            'id': 'id',
            'display_name': 'displayName',
            'time_created': 'timeCreated',
            'time_last_modified': 'timeLastModified',
            'description': 'description',
            'query': 'query',
            'defined_tags': 'definedTags',
            'freeform_tags': 'freeformTags'
        }

        self._id = None
        self._display_name = None
        self._time_created = None
        self._time_last_modified = None
        self._description = None
        self._query = None
        self._defined_tags = None
        self._freeform_tags = None

    @property
    def id(self):
        """
        **[Required]** Gets the id of this LogIncludedSearch.
        The OCID of the resource.


        :return: The id of this LogIncludedSearch.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id):
        """
        Sets the id of this LogIncludedSearch.
        The OCID of the resource.


        :param id: The id of this LogIncludedSearch.
        :type: str
        """
        self._id = id

    @property
    def display_name(self):
        """
        **[Required]** Gets the display_name of this LogIncludedSearch.
        The user-friendly display name. This must be unique within the enclosing resource,
        and it's changeable. Avoid entering confidential information.


        :return: The display_name of this LogIncludedSearch.
        :rtype: str
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        """
        Sets the display_name of this LogIncludedSearch.
        The user-friendly display name. This must be unique within the enclosing resource,
        and it's changeable. Avoid entering confidential information.


        :param display_name: The display_name of this LogIncludedSearch.
        :type: str
        """
        self._display_name = display_name

    @property
    def time_created(self):
        """
        Gets the time_created of this LogIncludedSearch.
        Time the resource was created.


        :return: The time_created of this LogIncludedSearch.
        :rtype: datetime
        """
        return self._time_created

    @time_created.setter
    def time_created(self, time_created):
        """
        Sets the time_created of this LogIncludedSearch.
        Time the resource was created.


        :param time_created: The time_created of this LogIncludedSearch.
        :type: datetime
        """
        self._time_created = time_created

    @property
    def time_last_modified(self):
        """
        Gets the time_last_modified of this LogIncludedSearch.
        Time the resource was last modified.


        :return: The time_last_modified of this LogIncludedSearch.
        :rtype: datetime
        """
        return self._time_last_modified

    @time_last_modified.setter
    def time_last_modified(self, time_last_modified):
        """
        Sets the time_last_modified of this LogIncludedSearch.
        Time the resource was last modified.


        :param time_last_modified: The time_last_modified of this LogIncludedSearch.
        :type: datetime
        """
        self._time_last_modified = time_last_modified

    @property
    def description(self):
        """
        Gets the description of this LogIncludedSearch.
        Description for this resource.


        :return: The description of this LogIncludedSearch.
        :rtype: str
        """
        return self._description

    @description.setter
    def description(self, description):
        """
        Sets the description of this LogIncludedSearch.
        Description for this resource.


        :param description: The description of this LogIncludedSearch.
        :type: str
        """
        self._description = description

    @property
    def query(self):
        """
        **[Required]** Gets the query of this LogIncludedSearch.
        The search query that is saved.


        :return: The query of this LogIncludedSearch.
        :rtype: str
        """
        return self._query

    @query.setter
    def query(self, query):
        """
        Sets the query of this LogIncludedSearch.
        The search query that is saved.


        :param query: The query of this LogIncludedSearch.
        :type: str
        """
        self._query = query

    @property
    def defined_tags(self):
        """
        Gets the defined_tags of this LogIncludedSearch.
        Defined tags for this resource. Each key is predefined and scoped to a
        namespace. For more information, see `Resource Tags`__.

        Example: `{\"Operations\": {\"CostCenter\": \"42\"}}`

        __ https://docs.cloud.oracle.com/Content/General/Concepts/resourcetags.htm


        :return: The defined_tags of this LogIncludedSearch.
        :rtype: dict(str, dict(str, object))
        """
        return self._defined_tags

    @defined_tags.setter
    def defined_tags(self, defined_tags):
        """
        Sets the defined_tags of this LogIncludedSearch.
        Defined tags for this resource. Each key is predefined and scoped to a
        namespace. For more information, see `Resource Tags`__.

        Example: `{\"Operations\": {\"CostCenter\": \"42\"}}`

        __ https://docs.cloud.oracle.com/Content/General/Concepts/resourcetags.htm


        :param defined_tags: The defined_tags of this LogIncludedSearch.
        :type: dict(str, dict(str, object))
        """
        self._defined_tags = defined_tags

    @property
    def freeform_tags(self):
        """
        Gets the freeform_tags of this LogIncludedSearch.
        Free-form tags for this resource. Each tag is a simple key-value pair with no
        predefined name, type, or namespace. For more information, see `Resource Tags`__.
        Example: `{\"Department\": \"Finance\"}`

        __ https://docs.cloud.oracle.com/Content/General/Concepts/resourcetags.htm


        :return: The freeform_tags of this LogIncludedSearch.
        :rtype: dict(str, str)
        """
        return self._freeform_tags

    @freeform_tags.setter
    def freeform_tags(self, freeform_tags):
        """
        Sets the freeform_tags of this LogIncludedSearch.
        Free-form tags for this resource. Each tag is a simple key-value pair with no
        predefined name, type, or namespace. For more information, see `Resource Tags`__.
        Example: `{\"Department\": \"Finance\"}`

        __ https://docs.cloud.oracle.com/Content/General/Concepts/resourcetags.htm


        :param freeform_tags: The freeform_tags of this LogIncludedSearch.
        :type: dict(str, str)
        """
        self._freeform_tags = freeform_tags

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
