# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class StringListDetails(object):
    """
    StringListDetails
    """

    def __init__(self, **kwargs):
        """
        Initializes a new StringListDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param list:
            The value to assign to the list property of this StringListDetails.
        :type list: list[str]

        """
        self.swagger_types = {
            'list': 'list[str]'
        }

        self.attribute_map = {
            'list': 'list'
        }

        self._list = None

    @property
    def list(self):
        """
        Gets the list of this StringListDetails.
        string list


        :return: The list of this StringListDetails.
        :rtype: list[str]
        """
        return self._list

    @list.setter
    def list(self, list):
        """
        Sets the list of this StringListDetails.
        string list


        :param list: The list of this StringListDetails.
        :type: list[str]
        """
        self._list = list

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
