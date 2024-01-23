# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import oci  # noqa: F401
from oci.util import WAIT_RESOURCE_NOT_FOUND  # noqa: F401


class FusionEnvironmentFamilyClientCompositeOperations(object):
    """
    This class provides a wrapper around :py:class:`~oci.fusion_apps.FusionEnvironmentFamilyClient` and offers convenience methods
    for operations that would otherwise need to be chained together. For example, instead of performing an action
    on a resource (e.g. launching an instance, creating a load balancer) and then using a waiter to wait for the resource
    to enter a given state, you can call a single method in this class to accomplish the same functionality
    """

    def __init__(self, client, **kwargs):
        """
        Creates a new FusionEnvironmentFamilyClientCompositeOperations object

        :param FusionEnvironmentFamilyClient client:
            The service client which will be wrapped by this object
        """
        self.client = client

    def change_fusion_environment_family_compartment_and_wait_for_state(self, fusion_environment_family_id, change_fusion_environment_family_compartment_details, wait_for_states=[], operation_kwargs={}, waiter_kwargs={}):
        """
        Calls :py:func:`~oci.fusion_apps.FusionEnvironmentFamilyClient.change_fusion_environment_family_compartment` and waits for the :py:class:`~oci.fusion_apps.models.WorkRequest`
        to enter the given state(s).

        :param str fusion_environment_family_id: (required)
            The unique identifier (OCID) of the FusionEnvironmentFamily.

        :param oci.fusion_apps.models.ChangeFusionEnvironmentFamilyCompartmentDetails change_fusion_environment_family_compartment_details: (required)
            Details for the compartment move.

        :param list[str] wait_for_states:
            An array of states to wait on. These should be valid values for :py:attr:`~oci.fusion_apps.models.WorkRequest.status`

        :param dict operation_kwargs:
            A dictionary of keyword arguments to pass to :py:func:`~oci.fusion_apps.FusionEnvironmentFamilyClient.change_fusion_environment_family_compartment`

        :param dict waiter_kwargs:
            A dictionary of keyword arguments to pass to the :py:func:`oci.wait_until` function. For example, you could pass ``max_interval_seconds`` or ``max_interval_seconds``
            as dictionary keys to modify how long the waiter function will wait between retries and the maximum amount of time it will wait
        """
        operation_result = self.client.change_fusion_environment_family_compartment(fusion_environment_family_id, change_fusion_environment_family_compartment_details, **operation_kwargs)
        if not wait_for_states:
            return operation_result

        lowered_wait_for_states = [w.lower() for w in wait_for_states]
        wait_for_resource_id = operation_result.headers['opc-work-request-id']

        try:
            waiter_result = oci.wait_until(
                self.client,
                self.client.get_work_request(wait_for_resource_id),
                evaluate_response=lambda r: getattr(r.data, 'status') and getattr(r.data, 'status').lower() in lowered_wait_for_states,
                **waiter_kwargs
            )
            result_to_return = waiter_result

            return result_to_return
        except Exception as e:
            raise oci.exceptions.CompositeOperationError(partial_results=[operation_result], cause=e)

    def create_fusion_environment_family_and_wait_for_state(self, create_fusion_environment_family_details, wait_for_states=[], operation_kwargs={}, waiter_kwargs={}):
        """
        Calls :py:func:`~oci.fusion_apps.FusionEnvironmentFamilyClient.create_fusion_environment_family` and waits for the :py:class:`~oci.fusion_apps.models.WorkRequest`
        to enter the given state(s).

        :param oci.fusion_apps.models.CreateFusionEnvironmentFamilyDetails create_fusion_environment_family_details: (required)
            Details for the new FusionEnvironmentFamily.

        :param list[str] wait_for_states:
            An array of states to wait on. These should be valid values for :py:attr:`~oci.fusion_apps.models.WorkRequest.status`

        :param dict operation_kwargs:
            A dictionary of keyword arguments to pass to :py:func:`~oci.fusion_apps.FusionEnvironmentFamilyClient.create_fusion_environment_family`

        :param dict waiter_kwargs:
            A dictionary of keyword arguments to pass to the :py:func:`oci.wait_until` function. For example, you could pass ``max_interval_seconds`` or ``max_interval_seconds``
            as dictionary keys to modify how long the waiter function will wait between retries and the maximum amount of time it will wait
        """
        operation_result = self.client.create_fusion_environment_family(create_fusion_environment_family_details, **operation_kwargs)
        if not wait_for_states:
            return operation_result

        lowered_wait_for_states = [w.lower() for w in wait_for_states]
        wait_for_resource_id = operation_result.headers['opc-work-request-id']

        try:
            waiter_result = oci.wait_until(
                self.client,
                self.client.get_work_request(wait_for_resource_id),
                evaluate_response=lambda r: getattr(r.data, 'status') and getattr(r.data, 'status').lower() in lowered_wait_for_states,
                **waiter_kwargs
            )
            result_to_return = waiter_result

            return result_to_return
        except Exception as e:
            raise oci.exceptions.CompositeOperationError(partial_results=[operation_result], cause=e)

    def delete_fusion_environment_family_and_wait_for_state(self, fusion_environment_family_id, wait_for_states=[], operation_kwargs={}, waiter_kwargs={}):
        """
        Calls :py:func:`~oci.fusion_apps.FusionEnvironmentFamilyClient.delete_fusion_environment_family` and waits for the :py:class:`~oci.fusion_apps.models.WorkRequest`
        to enter the given state(s).

        :param str fusion_environment_family_id: (required)
            The unique identifier (OCID) of the FusionEnvironmentFamily.

        :param list[str] wait_for_states:
            An array of states to wait on. These should be valid values for :py:attr:`~oci.fusion_apps.models.WorkRequest.status`

        :param dict operation_kwargs:
            A dictionary of keyword arguments to pass to :py:func:`~oci.fusion_apps.FusionEnvironmentFamilyClient.delete_fusion_environment_family`

        :param dict waiter_kwargs:
            A dictionary of keyword arguments to pass to the :py:func:`oci.wait_until` function. For example, you could pass ``max_interval_seconds`` or ``max_interval_seconds``
            as dictionary keys to modify how long the waiter function will wait between retries and the maximum amount of time it will wait
        """
        operation_result = None
        try:
            operation_result = self.client.delete_fusion_environment_family(fusion_environment_family_id, **operation_kwargs)
        except oci.exceptions.ServiceError as e:
            if e.status == 404:
                return WAIT_RESOURCE_NOT_FOUND
            else:
                raise e

        if not wait_for_states:
            return operation_result

        lowered_wait_for_states = [w.lower() for w in wait_for_states]
        wait_for_resource_id = operation_result.headers['opc-work-request-id']

        try:
            waiter_result = oci.wait_until(
                self.client,
                self.client.get_work_request(wait_for_resource_id),
                evaluate_response=lambda r: getattr(r.data, 'status') and getattr(r.data, 'status').lower() in lowered_wait_for_states,
                **waiter_kwargs
            )
            result_to_return = waiter_result

            return result_to_return
        except Exception as e:
            raise oci.exceptions.CompositeOperationError(partial_results=[operation_result], cause=e)

    def update_fusion_environment_family_and_wait_for_state(self, fusion_environment_family_id, update_fusion_environment_family_details, wait_for_states=[], operation_kwargs={}, waiter_kwargs={}):
        """
        Calls :py:func:`~oci.fusion_apps.FusionEnvironmentFamilyClient.update_fusion_environment_family` and waits for the :py:class:`~oci.fusion_apps.models.WorkRequest`
        to enter the given state(s).

        :param str fusion_environment_family_id: (required)
            The unique identifier (OCID) of the FusionEnvironmentFamily.

        :param oci.fusion_apps.models.UpdateFusionEnvironmentFamilyDetails update_fusion_environment_family_details: (required)
            The information to be updated.

        :param list[str] wait_for_states:
            An array of states to wait on. These should be valid values for :py:attr:`~oci.fusion_apps.models.WorkRequest.status`

        :param dict operation_kwargs:
            A dictionary of keyword arguments to pass to :py:func:`~oci.fusion_apps.FusionEnvironmentFamilyClient.update_fusion_environment_family`

        :param dict waiter_kwargs:
            A dictionary of keyword arguments to pass to the :py:func:`oci.wait_until` function. For example, you could pass ``max_interval_seconds`` or ``max_interval_seconds``
            as dictionary keys to modify how long the waiter function will wait between retries and the maximum amount of time it will wait
        """
        operation_result = self.client.update_fusion_environment_family(fusion_environment_family_id, update_fusion_environment_family_details, **operation_kwargs)
        if not wait_for_states:
            return operation_result

        lowered_wait_for_states = [w.lower() for w in wait_for_states]
        wait_for_resource_id = operation_result.headers['opc-work-request-id']

        try:
            waiter_result = oci.wait_until(
                self.client,
                self.client.get_work_request(wait_for_resource_id),
                evaluate_response=lambda r: getattr(r.data, 'status') and getattr(r.data, 'status').lower() in lowered_wait_for_states,
                **waiter_kwargs
            )
            result_to_return = waiter_result

            return result_to_return
        except Exception as e:
            raise oci.exceptions.CompositeOperationError(partial_results=[operation_result], cause=e)
