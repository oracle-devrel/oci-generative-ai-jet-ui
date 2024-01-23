# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class ServiceTenancy(object):
    """
    Tenancy where Log Analytics Application belongs to
    """

    def __init__(self, **kwargs):
        """
        Initializes a new ServiceTenancy object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param tenancy_id:
            The value to assign to the tenancy_id property of this ServiceTenancy.
        :type tenancy_id: str

        """
        self.swagger_types = {
            'tenancy_id': 'str'
        }

        self.attribute_map = {
            'tenancy_id': 'tenancyId'
        }

        self._tenancy_id = None

    @property
    def tenancy_id(self):
        """
        **[Required]** Gets the tenancy_id of this ServiceTenancy.
        Tenancy ID


        :return: The tenancy_id of this ServiceTenancy.
        :rtype: str
        """
        return self._tenancy_id

    @tenancy_id.setter
    def tenancy_id(self, tenancy_id):
        """
        Sets the tenancy_id of this ServiceTenancy.
        Tenancy ID


        :param tenancy_id: The tenancy_id of this ServiceTenancy.
        :type: str
        """
        self._tenancy_id = tenancy_id

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
