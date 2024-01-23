# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class ParLink(object):
    """
    Pre-Authenticated Request Link for ODMS Agent log use.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new ParLink object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param par_link:
            The value to assign to the par_link property of this ParLink.
        :type par_link: str

        """
        self.swagger_types = {
            'par_link': 'str'
        }

        self.attribute_map = {
            'par_link': 'parLink'
        }

        self._par_link = None

    @property
    def par_link(self):
        """
        **[Required]** Gets the par_link of this ParLink.
        Pre-Authenticated Request URI.


        :return: The par_link of this ParLink.
        :rtype: str
        """
        return self._par_link

    @par_link.setter
    def par_link(self, par_link):
        """
        Sets the par_link of this ParLink.
        Pre-Authenticated Request URI.


        :param par_link: The par_link of this ParLink.
        :type: str
        """
        self._par_link = par_link

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
