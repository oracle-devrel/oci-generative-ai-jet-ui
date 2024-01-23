# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class UpdatablePackageSummary(object):
    """
    A software package available for update on a managed instance
    """

    def __init__(self, **kwargs):
        """
        Initializes a new UpdatablePackageSummary object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param display_name:
            The value to assign to the display_name property of this UpdatablePackageSummary.
        :type display_name: str

        :param name:
            The value to assign to the name property of this UpdatablePackageSummary.
        :type name: str

        :param available_package_name:
            The value to assign to the available_package_name property of this UpdatablePackageSummary.
        :type available_package_name: str

        :param type:
            The value to assign to the type property of this UpdatablePackageSummary.
        :type type: str

        :param installed_version:
            The value to assign to the installed_version property of this UpdatablePackageSummary.
        :type installed_version: str

        :param available_version:
            The value to assign to the available_version property of this UpdatablePackageSummary.
        :type available_version: str

        :param architecture:
            The value to assign to the architecture property of this UpdatablePackageSummary.
        :type architecture: str

        :param software_sources:
            The value to assign to the software_sources property of this UpdatablePackageSummary.
        :type software_sources: list[SoftwareSourceId]

        """
        self.swagger_types = {
            'display_name': 'str',
            'name': 'str',
            'available_package_name': 'str',
            'type': 'str',
            'installed_version': 'str',
            'available_version': 'str',
            'architecture': 'str',
            'software_sources': 'list[SoftwareSourceId]'
        }

        self.attribute_map = {
            'display_name': 'displayName',
            'name': 'name',
            'available_package_name': 'availablePackageName',
            'type': 'type',
            'installed_version': 'installedVersion',
            'available_version': 'availableVersion',
            'architecture': 'architecture',
            'software_sources': 'softwareSources'
        }

        self._display_name = None
        self._name = None
        self._available_package_name = None
        self._type = None
        self._installed_version = None
        self._available_version = None
        self._architecture = None
        self._software_sources = None

    @property
    def display_name(self):
        """
        **[Required]** Gets the display_name of this UpdatablePackageSummary.
        Package name


        :return: The display_name of this UpdatablePackageSummary.
        :rtype: str
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        """
        Sets the display_name of this UpdatablePackageSummary.
        Package name


        :param display_name: The display_name of this UpdatablePackageSummary.
        :type: str
        """
        self._display_name = display_name

    @property
    def name(self):
        """
        **[Required]** Gets the name of this UpdatablePackageSummary.
        Unique name for the package.


        :return: The name of this UpdatablePackageSummary.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Sets the name of this UpdatablePackageSummary.
        Unique name for the package.


        :param name: The name of this UpdatablePackageSummary.
        :type: str
        """
        self._name = name

    @property
    def available_package_name(self):
        """
        Gets the available_package_name of this UpdatablePackageSummary.
        Unique name for the package available for update.


        :return: The available_package_name of this UpdatablePackageSummary.
        :rtype: str
        """
        return self._available_package_name

    @available_package_name.setter
    def available_package_name(self, available_package_name):
        """
        Sets the available_package_name of this UpdatablePackageSummary.
        Unique name for the package available for update.


        :param available_package_name: The available_package_name of this UpdatablePackageSummary.
        :type: str
        """
        self._available_package_name = available_package_name

    @property
    def type(self):
        """
        **[Required]** Gets the type of this UpdatablePackageSummary.
        Type of the update.


        :return: The type of this UpdatablePackageSummary.
        :rtype: str
        """
        return self._type

    @type.setter
    def type(self, type):
        """
        Sets the type of this UpdatablePackageSummary.
        Type of the update.


        :param type: The type of this UpdatablePackageSummary.
        :type: str
        """
        self._type = type

    @property
    def installed_version(self):
        """
        **[Required]** Gets the installed_version of this UpdatablePackageSummary.
        Version of the installed package


        :return: The installed_version of this UpdatablePackageSummary.
        :rtype: str
        """
        return self._installed_version

    @installed_version.setter
    def installed_version(self, installed_version):
        """
        Sets the installed_version of this UpdatablePackageSummary.
        Version of the installed package


        :param installed_version: The installed_version of this UpdatablePackageSummary.
        :type: str
        """
        self._installed_version = installed_version

    @property
    def available_version(self):
        """
        **[Required]** Gets the available_version of this UpdatablePackageSummary.
        Version of the package available for update


        :return: The available_version of this UpdatablePackageSummary.
        :rtype: str
        """
        return self._available_version

    @available_version.setter
    def available_version(self, available_version):
        """
        Sets the available_version of this UpdatablePackageSummary.
        Version of the package available for update


        :param available_version: The available_version of this UpdatablePackageSummary.
        :type: str
        """
        self._available_version = available_version

    @property
    def architecture(self):
        """
        Gets the architecture of this UpdatablePackageSummary.
        The architecture for which this package was built


        :return: The architecture of this UpdatablePackageSummary.
        :rtype: str
        """
        return self._architecture

    @architecture.setter
    def architecture(self, architecture):
        """
        Sets the architecture of this UpdatablePackageSummary.
        The architecture for which this package was built


        :param architecture: The architecture of this UpdatablePackageSummary.
        :type: str
        """
        self._architecture = architecture

    @property
    def software_sources(self):
        """
        Gets the software_sources of this UpdatablePackageSummary.
        list of software sources that provide the software package


        :return: The software_sources of this UpdatablePackageSummary.
        :rtype: list[SoftwareSourceId]
        """
        return self._software_sources

    @software_sources.setter
    def software_sources(self, software_sources):
        """
        Sets the software_sources of this UpdatablePackageSummary.
        list of software sources that provide the software package


        :param software_sources: The software_sources of this UpdatablePackageSummary.
        :type: list[SoftwareSourceId]
        """
        self._software_sources = software_sources

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
