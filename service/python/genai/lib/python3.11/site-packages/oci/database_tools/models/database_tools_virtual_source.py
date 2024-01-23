# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class DatabaseToolsVirtualSource(object):
    """
    A VCN `OCID`__ and a list of CIDR blocks.

    __ https://docs.cloud.oracle.com/Content/General/Concepts/identifiers.htm
    """

    def __init__(self, **kwargs):
        """
        Initializes a new DatabaseToolsVirtualSource object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param vcn_id:
            The value to assign to the vcn_id property of this DatabaseToolsVirtualSource.
        :type vcn_id: str

        :param ip_ranges:
            The value to assign to the ip_ranges property of this DatabaseToolsVirtualSource.
        :type ip_ranges: list[str]

        """
        self.swagger_types = {
            'vcn_id': 'str',
            'ip_ranges': 'list[str]'
        }

        self.attribute_map = {
            'vcn_id': 'vcnId',
            'ip_ranges': 'ipRanges'
        }

        self._vcn_id = None
        self._ip_ranges = None

    @property
    def vcn_id(self):
        """
        Gets the vcn_id of this DatabaseToolsVirtualSource.
        The `OCID`__ of a VCN.

        __ https://docs.cloud.oracle.com/Content/General/Concepts/identifiers.htm


        :return: The vcn_id of this DatabaseToolsVirtualSource.
        :rtype: str
        """
        return self._vcn_id

    @vcn_id.setter
    def vcn_id(self, vcn_id):
        """
        Sets the vcn_id of this DatabaseToolsVirtualSource.
        The `OCID`__ of a VCN.

        __ https://docs.cloud.oracle.com/Content/General/Concepts/identifiers.htm


        :param vcn_id: The vcn_id of this DatabaseToolsVirtualSource.
        :type: str
        """
        self._vcn_id = vcn_id

    @property
    def ip_ranges(self):
        """
        Gets the ip_ranges of this DatabaseToolsVirtualSource.
        A list of CIDR blocks.


        :return: The ip_ranges of this DatabaseToolsVirtualSource.
        :rtype: list[str]
        """
        return self._ip_ranges

    @ip_ranges.setter
    def ip_ranges(self, ip_ranges):
        """
        Sets the ip_ranges of this DatabaseToolsVirtualSource.
        A list of CIDR blocks.


        :param ip_ranges: The ip_ranges of this DatabaseToolsVirtualSource.
        :type: list[str]
        """
        self._ip_ranges = ip_ranges

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
