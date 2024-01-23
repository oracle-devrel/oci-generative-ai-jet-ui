# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class FieldMap(object):
    """
    FieldMap
    """

    def __init__(self, **kwargs):
        """
        Initializes a new FieldMap object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param lookup_field:
            The value to assign to the lookup_field property of this FieldMap.
        :type lookup_field: str

        :param maps_to:
            The value to assign to the maps_to property of this FieldMap.
        :type maps_to: str

        """
        self.swagger_types = {
            'lookup_field': 'str',
            'maps_to': 'str'
        }

        self.attribute_map = {
            'lookup_field': 'lookupField',
            'maps_to': 'mapsTo'
        }

        self._lookup_field = None
        self._maps_to = None

    @property
    def lookup_field(self):
        """
        Gets the lookup_field of this FieldMap.
        loopup field


        :return: The lookup_field of this FieldMap.
        :rtype: str
        """
        return self._lookup_field

    @lookup_field.setter
    def lookup_field(self, lookup_field):
        """
        Sets the lookup_field of this FieldMap.
        loopup field


        :param lookup_field: The lookup_field of this FieldMap.
        :type: str
        """
        self._lookup_field = lookup_field

    @property
    def maps_to(self):
        """
        Gets the maps_to of this FieldMap.
        maps to


        :return: The maps_to of this FieldMap.
        :rtype: str
        """
        return self._maps_to

    @maps_to.setter
    def maps_to(self, maps_to):
        """
        Sets the maps_to of this FieldMap.
        maps to


        :param maps_to: The maps_to of this FieldMap.
        :type: str
        """
        self._maps_to = maps_to

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
