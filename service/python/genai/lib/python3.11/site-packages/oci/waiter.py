# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import time

from .exceptions import MaximumWaitTimeExceeded, WaitUntilNotSupported, ServiceError
from .util import WAIT_RESOURCE_NOT_FOUND
from . import retry
from oci.work_requests.models import WorkRequest

MAX_RETRIES_ON_401 = 2


def wait_until(client, response, property=None, state=None, max_interval_seconds=30, max_wait_seconds=1200, succeed_on_not_found=False, **kwargs):
    """Wait until the value of the given property in the response data has the given value.

    This will block the current thread until either the
    the desired state or the maximum wait time is reached. This is only
    supported for responses resulting from GET operations. A typical use
    case is to wait on an instance until it is in a running state.

    Although this can be run on any property of the data resulting from any
    GET operation, the most common use case is to check state properties on
    operations that GET a single object.

    The wait will poll at an increasing interval up to 'max_interval_seconds'
    for a maximum total time of 'max_wait_seconds'. If the maximum time
    is exceeded, then it will raise a MaximumWaitTimeExceeded error.

    On successful completion the final Response object will be returned. The
    original Response object will not be altered.

    If any responses result in an error, then the error will be thrown as normal
    resulting in the wait being aborted.

    :param client: A client we can use to call the service to periodically retrieve data.
    :param response: A Response object resulting from a GET operation.
    :param property: A string with the name of the property from the response data to evaluate.
        For example, 'state'.
    :param state: The value of the property that will indicate successful completion of the wait.
        Type corresponds to the property type.
    :param max_interval_seconds: (optional) The maximum interval between queries, in seconds.
        Defaults to 30 seconds.
    :param max_wait_seconds: (optional) The maximum time to wait, in seconds.
        Defaults to 1200 seconds.
    :param succeed_on_not_found: (optional) A boolean determining whether or not the waiter should return successfully
        if the data we're waiting on is not found (e.g. a 404 is returned from the service). This defaults to
        False and so a 404 would cause an exception to be thrown by this function. Setting it to True may be useful
        in scenarios when waiting for a resource to be terminated/deleted since it is possible that the resource would
        not be returned by the a GET call anymore.
    :param evaluate_response: (optional) A function which can be used to evaluate the response from the GET operation.
        This is a single argument function which takes in the response from the GET operation. If this function is
        supplied, then the 'property' argument cannot be supplied. It is expected that this function return a truthy
        value to signify that a condition has passed and the wait_until function should return, and a falsey value otherwise.
    :param wait_callback: (optional) A function which will be called each time that we have to do an initial wait (i.e.
        because the property of the resource was not in the correct state, or the ``evaluate_response`` function returned
         False). This function should take two arguments - the first argument is the number of times we have checked the
         resource, and the second argument is the result of the most recent check.
    :param fetch_func: (optional) This function will be called to fetch the updated state from the server.
        This can be used if the call to check for state needs to be more complex than a single GET request.
        For example, if the goal is to wait until an item appears in a list, fetch_func can be a function
        that paginates through a full list on the server.

    :return: The final response, which will contain the property in the specified state.

        If the ``succeed_on_not_found`` parameter is set to True and the data was not then ``oci.waiter.
        WAIT_RESOURCE_NOT_FOUND`` will be returned. This is a :py:class:`~oci.util.Sentinel` which is not truthy and
        holds an internal name of ``WaitResourceNotFound``.
    """

    if kwargs.get('evaluate_response') and (property):
        raise ValueError('Invalid wait_until configuration - can not provide both evaluate_response function and property argument, only one should be specified')
    elif not (kwargs.get('evaluate_response') or property):
        raise RuntimeError('Invalid wait_until configuration - neither a property argument, nor an evaluate_response function, have been specified')

    if kwargs.get('fetch_func') is None:
        # if no custom fetch_func is provided, we only support waiting on a GET request
        if response.request.method.lower() != 'get':
            raise WaitUntilNotSupported('wait_until is only supported for get operations.')

        # by default, re-issue response.request
        def default_fetch_func(response=None):
            return retry.DEFAULT_RETRY_STRATEGY.make_retrying_call(client.base_client.request, response.request)

        kwargs['fetch_func'] = default_fetch_func

    if property and not hasattr(response.data, property):
        raise ValueError('Response data does not contain the given property.')

    sleep_interval_seconds = 1
    start_time = time.time()

    times_checked = 0
    retry_count_401 = 0
    while True:
        if property:
            if isinstance(state, tuple):
                if getattr(response.data, property) in state:
                    return response
            elif getattr(response.data, property) == state:
                return response
        elif kwargs.get('evaluate_response')(response):
            return response

        if kwargs.get('wait_callback') and times_checked > 0:
            kwargs['wait_callback'](times_checked, response)

        elapsed_seconds = (time.time() - start_time)

        if elapsed_seconds + sleep_interval_seconds > max_wait_seconds:
            if max_wait_seconds <= elapsed_seconds:
                raise MaximumWaitTimeExceeded('Maximum wait time has been exceeded.')

        time.sleep(sleep_interval_seconds)

        # Double the sleep each time up to the maximum.
        sleep_interval_seconds = min(sleep_interval_seconds * 2, max_interval_seconds)

        try:
            response = kwargs.get('fetch_func')(response=response)
            retry_count_401 = 0
            times_checked += 1
        except ServiceError as se:
            if se.status == 404:
                if not succeed_on_not_found:
                    raise
                else:
                    # Returning the last good response may be disingenuous so instead return
                    # a sentinel flagging that the resource we tried to wait on was not
                    # found
                    return WAIT_RESOURCE_NOT_FOUND
            elif se.status == 401 and retry_count_401 < MAX_RETRIES_ON_401 and \
                    client.base_client.is_instance_principal_or_resource_principal_signer():
                retry_count_401 += 1
                client.base_client.signer.refresh_security_token()
            else:
                raise


# list of termination states for work request service used by composite operation waiters
_WORK_REQUEST_TERMINATION_STATES = [
    WorkRequest.STATUS_SUCCEEDED,
    WorkRequest.STATUS_FAILED,
    WorkRequest.STATUS_CANCELED
]
