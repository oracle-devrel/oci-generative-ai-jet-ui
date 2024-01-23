# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class RegisterEntityTypesDetails(object):
    """
    Entity Types Definition
    """

    def __init__(self, **kwargs):
        """
        Initializes a new RegisterEntityTypesDetails object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param entity_types:
            The value to assign to the entity_types property of this RegisterEntityTypesDetails.
        :type entity_types: list[OutOfBoxEntityTypeDetails]

        """
        self.swagger_types = {
            'entity_types': 'list[OutOfBoxEntityTypeDetails]'
        }

        self.attribute_map = {
            'entity_types': 'entityTypes'
        }

        self._entity_types = None

    @property
    def entity_types(self):
        """
        **[Required]** Gets the entity_types of this RegisterEntityTypesDetails.
        New Entity Type Create Definition


        :return: The entity_types of this RegisterEntityTypesDetails.
        :rtype: list[OutOfBoxEntityTypeDetails]
        """
        return self._entity_types

    @entity_types.setter
    def entity_types(self, entity_types):
        """
        Sets the entity_types of this RegisterEntityTypesDetails.
        New Entity Type Create Definition


        :param entity_types: The entity_types of this RegisterEntityTypesDetails.
        :type: list[OutOfBoxEntityTypeDetails]
        """
        self._entity_types = entity_types

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
