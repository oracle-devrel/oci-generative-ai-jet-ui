# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class GenerateToken(object):
    """
    ODMS Agent token details.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new GenerateToken object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param rpt_blob:
            The value to assign to the rpt_blob property of this GenerateToken.
        :type rpt_blob: str

        """
        self.swagger_types = {
            'rpt_blob': 'str'
        }

        self.attribute_map = {
            'rpt_blob': 'rptBlob'
        }

        self._rpt_blob = None

    @property
    def rpt_blob(self):
        """
        **[Required]** Gets the rpt_blob of this GenerateToken.
        Resource Principals Token in serialized form.


        :return: The rpt_blob of this GenerateToken.
        :rtype: str
        """
        return self._rpt_blob

    @rpt_blob.setter
    def rpt_blob(self, rpt_blob):
        """
        Sets the rpt_blob of this GenerateToken.
        Resource Principals Token in serialized form.


        :param rpt_blob: The rpt_blob of this GenerateToken.
        :type: str
        """
        self._rpt_blob = rpt_blob

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
