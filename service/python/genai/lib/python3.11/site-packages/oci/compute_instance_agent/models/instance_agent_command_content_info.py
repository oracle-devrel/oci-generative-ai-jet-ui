# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class InstanceAgentCommandContentInfo(object):
    """
    The command content.
    """

    def __init__(self, **kwargs):
        """
        Initializes a new InstanceAgentCommandContentInfo object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param instance_agent_command_id:
            The value to assign to the instance_agent_command_id property of this InstanceAgentCommandContentInfo.
        :type instance_agent_command_id: str

        :param compartment_id:
            The value to assign to the compartment_id property of this InstanceAgentCommandContentInfo.
        :type compartment_id: str

        :param time_created:
            The value to assign to the time_created property of this InstanceAgentCommandContentInfo.
        :type time_created: datetime

        :param time_updated:
            The value to assign to the time_updated property of this InstanceAgentCommandContentInfo.
        :type time_updated: datetime

        :param is_canceled:
            The value to assign to the is_canceled property of this InstanceAgentCommandContentInfo.
        :type is_canceled: bool

        :param execution_time_out_in_seconds:
            The value to assign to the execution_time_out_in_seconds property of this InstanceAgentCommandContentInfo.
        :type execution_time_out_in_seconds: int

        :param content:
            The value to assign to the content property of this InstanceAgentCommandContentInfo.
        :type content: oci.compute_instance_agent.models.InstanceAgentCommandContent

        """
        self.swagger_types = {
            'instance_agent_command_id': 'str',
            'compartment_id': 'str',
            'time_created': 'datetime',
            'time_updated': 'datetime',
            'is_canceled': 'bool',
            'execution_time_out_in_seconds': 'int',
            'content': 'InstanceAgentCommandContent'
        }

        self.attribute_map = {
            'instance_agent_command_id': 'instanceAgentCommandId',
            'compartment_id': 'compartmentId',
            'time_created': 'timeCreated',
            'time_updated': 'timeUpdated',
            'is_canceled': 'isCanceled',
            'execution_time_out_in_seconds': 'executionTimeOutInSeconds',
            'content': 'content'
        }

        self._instance_agent_command_id = None
        self._compartment_id = None
        self._time_created = None
        self._time_updated = None
        self._is_canceled = None
        self._execution_time_out_in_seconds = None
        self._content = None

    @property
    def instance_agent_command_id(self):
        """
        **[Required]** Gets the instance_agent_command_id of this InstanceAgentCommandContentInfo.
        The command ocid


        :return: The instance_agent_command_id of this InstanceAgentCommandContentInfo.
        :rtype: str
        """
        return self._instance_agent_command_id

    @instance_agent_command_id.setter
    def instance_agent_command_id(self, instance_agent_command_id):
        """
        Sets the instance_agent_command_id of this InstanceAgentCommandContentInfo.
        The command ocid


        :param instance_agent_command_id: The instance_agent_command_id of this InstanceAgentCommandContentInfo.
        :type: str
        """
        self._instance_agent_command_id = instance_agent_command_id

    @property
    def compartment_id(self):
        """
        **[Required]** Gets the compartment_id of this InstanceAgentCommandContentInfo.
        The OCID of the compartment the command is created in.


        :return: The compartment_id of this InstanceAgentCommandContentInfo.
        :rtype: str
        """
        return self._compartment_id

    @compartment_id.setter
    def compartment_id(self, compartment_id):
        """
        Sets the compartment_id of this InstanceAgentCommandContentInfo.
        The OCID of the compartment the command is created in.


        :param compartment_id: The compartment_id of this InstanceAgentCommandContentInfo.
        :type: str
        """
        self._compartment_id = compartment_id

    @property
    def time_created(self):
        """
        Gets the time_created of this InstanceAgentCommandContentInfo.
        created at time of command.


        :return: The time_created of this InstanceAgentCommandContentInfo.
        :rtype: datetime
        """
        return self._time_created

    @time_created.setter
    def time_created(self, time_created):
        """
        Sets the time_created of this InstanceAgentCommandContentInfo.
        created at time of command.


        :param time_created: The time_created of this InstanceAgentCommandContentInfo.
        :type: datetime
        """
        self._time_created = time_created

    @property
    def time_updated(self):
        """
        Gets the time_updated of this InstanceAgentCommandContentInfo.
        updated time of command.


        :return: The time_updated of this InstanceAgentCommandContentInfo.
        :rtype: datetime
        """
        return self._time_updated

    @time_updated.setter
    def time_updated(self, time_updated):
        """
        Sets the time_updated of this InstanceAgentCommandContentInfo.
        updated time of command.


        :param time_updated: The time_updated of this InstanceAgentCommandContentInfo.
        :type: datetime
        """
        self._time_updated = time_updated

    @property
    def is_canceled(self):
        """
        Gets the is_canceled of this InstanceAgentCommandContentInfo.
        Whether the command has been canceled.


        :return: The is_canceled of this InstanceAgentCommandContentInfo.
        :rtype: bool
        """
        return self._is_canceled

    @is_canceled.setter
    def is_canceled(self, is_canceled):
        """
        Sets the is_canceled of this InstanceAgentCommandContentInfo.
        Whether the command has been canceled.


        :param is_canceled: The is_canceled of this InstanceAgentCommandContentInfo.
        :type: bool
        """
        self._is_canceled = is_canceled

    @property
    def execution_time_out_in_seconds(self):
        """
        Gets the execution_time_out_in_seconds of this InstanceAgentCommandContentInfo.
        The last command time.


        :return: The execution_time_out_in_seconds of this InstanceAgentCommandContentInfo.
        :rtype: int
        """
        return self._execution_time_out_in_seconds

    @execution_time_out_in_seconds.setter
    def execution_time_out_in_seconds(self, execution_time_out_in_seconds):
        """
        Sets the execution_time_out_in_seconds of this InstanceAgentCommandContentInfo.
        The last command time.


        :param execution_time_out_in_seconds: The execution_time_out_in_seconds of this InstanceAgentCommandContentInfo.
        :type: int
        """
        self._execution_time_out_in_seconds = execution_time_out_in_seconds

    @property
    def content(self):
        """
        **[Required]** Gets the content of this InstanceAgentCommandContentInfo.

        :return: The content of this InstanceAgentCommandContentInfo.
        :rtype: oci.compute_instance_agent.models.InstanceAgentCommandContent
        """
        return self._content

    @content.setter
    def content(self, content):
        """
        Sets the content of this InstanceAgentCommandContentInfo.

        :param content: The content of this InstanceAgentCommandContentInfo.
        :type: oci.compute_instance_agent.models.InstanceAgentCommandContent
        """
        self._content = content

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
