# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class DeleteOceInstanceDetails(object):
    """
    The information about the resource to be deleted.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new DeleteOceInstanceDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param idcs_access_token:
            The value to assign to the idcs_access_token property of this DeleteOceInstanceDetails.
        :type idcs_access_token: str

        """
        self.swagger_types = {
            'idcs_access_token': 'str'
        }

        self.attribute_map = {
            'idcs_access_token': 'idcsAccessToken'
        }

        self._idcs_access_token = None

    @property
    def idcs_access_token(self):
        """
        **[Required]** Gets the idcs_access_token of this DeleteOceInstanceDetails.
        IDCS access token identifying a stripe and service administrator user


        :return: The idcs_access_token of this DeleteOceInstanceDetails.
        :rtype: str
        """
        return self._idcs_access_token

    @idcs_access_token.setter
    def idcs_access_token(self, idcs_access_token):
        """
        Sets the idcs_access_token of this DeleteOceInstanceDetails.
        IDCS access token identifying a stripe and service administrator user


        :param idcs_access_token: The idcs_access_token of this DeleteOceInstanceDetails.
        :type: str
        """
        self._idcs_access_token = idcs_access_token

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
