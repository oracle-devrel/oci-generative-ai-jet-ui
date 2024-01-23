# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class DatabaseToolsAllowedNetworkSources(object):
    """
    Allow to restrict access to only requests that come from the specified public or virtual source IP addresses.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new DatabaseToolsAllowedNetworkSources object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param public_source_list:
            The value to assign to the public_source_list property of this DatabaseToolsAllowedNetworkSources.
        :type public_source_list: list[str]

        :param virtual_source_list:
            The value to assign to the virtual_source_list property of this DatabaseToolsAllowedNetworkSources.
        :type virtual_source_list: list[oci.database_tools.models.DatabaseToolsVirtualSource]

        """
        self.swagger_types = {
            'public_source_list': 'list[str]',
            'virtual_source_list': 'list[DatabaseToolsVirtualSource]'
        }

        self.attribute_map = {
            'public_source_list': 'publicSourceList',
            'virtual_source_list': 'virtualSourceList'
        }

        self._public_source_list = None
        self._virtual_source_list = None

    @property
    def public_source_list(self):
        """
        Gets the public_source_list of this DatabaseToolsAllowedNetworkSources.
        A list of allowed public IPs and CIDR blocks.


        :return: The public_source_list of this DatabaseToolsAllowedNetworkSources.
        :rtype: list[str]
        """
        return self._public_source_list

    @public_source_list.setter
    def public_source_list(self, public_source_list):
        """
        Sets the public_source_list of this DatabaseToolsAllowedNetworkSources.
        A list of allowed public IPs and CIDR blocks.


        :param public_source_list: The public_source_list of this DatabaseToolsAllowedNetworkSources.
        :type: list[str]
        """
        self._public_source_list = public_source_list

    @property
    def virtual_source_list(self):
        """
        Gets the virtual_source_list of this DatabaseToolsAllowedNetworkSources.
        A list of allowed VCN `OCID`__ and IP ranges pairs.
        Example:`\"vcnId\": \"ocid1.vcn.oc1.iad.aaaaaaaaexampleuniqueID\", \"ipRanges\": [ \"129.213.39.0/24\" ]`

        __ https://docs.cloud.oracle.com/Content/General/Concepts/identifiers.htm


        :return: The virtual_source_list of this DatabaseToolsAllowedNetworkSources.
        :rtype: list[oci.database_tools.models.DatabaseToolsVirtualSource]
        """
        return self._virtual_source_list

    @virtual_source_list.setter
    def virtual_source_list(self, virtual_source_list):
        """
        Sets the virtual_source_list of this DatabaseToolsAllowedNetworkSources.
        A list of allowed VCN `OCID`__ and IP ranges pairs.
        Example:`\"vcnId\": \"ocid1.vcn.oc1.iad.aaaaaaaaexampleuniqueID\", \"ipRanges\": [ \"129.213.39.0/24\" ]`

        __ https://docs.cloud.oracle.com/Content/General/Concepts/identifiers.htm


        :param virtual_source_list: The virtual_source_list of this DatabaseToolsAllowedNetworkSources.
        :type: list[oci.database_tools.models.DatabaseToolsVirtualSource]
        """
        self._virtual_source_list = virtual_source_list

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
