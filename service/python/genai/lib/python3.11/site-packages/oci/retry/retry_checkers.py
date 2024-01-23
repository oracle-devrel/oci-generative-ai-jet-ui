# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

# Contains helper classes that can say whether a retry should occur based on various criteria, such as a maximum number of retries being
# hit or the exception received from a service call (or the response from the service call if it didn't exception out).

from ..exceptions import ServiceError, RequestException, ConnectTimeout
from circuitbreaker import CircuitBreakerError
from oci._vendor.requests.exceptions import Timeout
from oci._vendor.requests.exceptions import ConnectionError as RequestsConnectionError
import logging
import threading

logger = logging.getLogger(__name__)

RETRYABLE_STATUSES_AND_CODES = {
    -1: [],
    409: ['IncorrectState'],
    429: []
}


class RetryCheckerContainer(object):
    """
    A container which holds at least one retry checker. This lets us chain together different retry checkers into an overall
    evaluation of whether we should retry a request.

    Checkers are evaluated in the order they appear in the provided list of checkers, and if one checker reports failure we
    consider this to be an overall failure and no more retries should happen.
    """

    def __init__(self, checkers, **kwargs):
        if not checkers:
            raise ValueError('At least one retry checker needs to be provided')
        self.checkers = checkers

    def add_checker(self, checker):
        self.checkers.append(checker)

    def should_retry(self, exception=None, response=None, **kwargs):
        """
        Determines if a retry should be performed based on either an exception or a response. We will
        retry if all the checkers held in this container indicate that they should retry; if any checker
        indicates that the call should not be retried then we will not retry.

        :param Exception exception:
            An exception received from the service

        :param Response response:
            The :class:`~oci.response.Response` received from a service call

        :return: True if we should retry, and False otherwise
        :rtype: Boolean
        """
        for c in self.checkers:
            if not c.should_retry(exception, response, **kwargs):
                return False

        return True


class BaseRetryChecker(object):
    """
    The base class from which all retry checkers should derive. This has no implementation but just defines the contract
    for a checker. Implementors can extend this class to define their own checking logic.
    """

    def __init__(self, **kwargs):
        pass

    def should_retry(self, exception=None, response=None, **kwargs):
        """
        Determines if a retry should be performed based on either an exception or a response.

        :param Exception exception:
            An exception received from the service

        :param Response response:
            The :class:`~oci.response.Response` received from a service call

        :return: True if we should retry, and False otherwise
        :rtype: Boolean
        """
        raise NotImplementedError('Subclasses should implement this')


class TotalTimeExceededRetryChecker(BaseRetryChecker):
    """
    A retry checker which can retry as long as some upper time limit (in seconds) has not been breached. This is intended
    for scenarios such as "keep retrying for 5 minutes". It is the responsiblity of the caller to track the total time
    elapsed - objects of this class will not track this.

    If not specified, the default time limit is 600 seconds (10 minutes).
    """

    def __init__(self, time_limit_seconds=600, **kwargs):
        super(TotalTimeExceededRetryChecker, self).__init__(**kwargs)
        self.time_limit_seconds = time_limit_seconds

    def should_retry(self, exception=None, response=None, **kwargs):
        return self.time_limit_seconds > kwargs.get('total_time_elapsed', 0)


class LimitBasedRetryChecker(BaseRetryChecker):
    """
    A retry checker which can retry as long as some threshold (# of attempts/tries) has not been breached.
    It is the responsiblity of the caller to track how many attempts/tries it has done - objects of this
    class will not track this.

    If not specified, the default number of tries allowed is 8. Tries are also assumed to be one-based (i.e. the
    first attempt/try is 1, the second is 2 etc)
    """

    def __init__(self, max_attempts=8, **kwargs):
        if max_attempts < 1:
            raise ValueError('The max number of attempts must be >= 1, with 1 indicating no retries')

        super(LimitBasedRetryChecker, self).__init__(**kwargs)
        self.max_attempts = max_attempts

    def should_retry(self, exception=None, response=None, **kwargs):
        return self.max_attempts > kwargs.get('current_attempt', 0)


class TimeoutConnectionAndServiceErrorRetryChecker(BaseRetryChecker):
    """
    A checker which will retry on certain exceptions. Retries are enabled for the following exception types:

        - Timeouts from the requests library (we will always retry on these)
        - ConnectionErrors from the requests library (we will always retry on these)
        - Built-in ConnectionErrors from Python 3
        - Service errors where the status is 500 or above (i.e. a server-side error, except 501)
        - Service errors where a status (e.g. 429) and, optionally, the code meet a given criteria

    The last item is configurable via dictionary where the key is some numeric status representing a HTTP status and the value
    is a list of strings with each string representing a textual error code (such as those error codes documented at
    https://docs.cloud.oracle.com/Content/API/References/apierrors.htm). If an empty list is provided, then
    only the numeric status is checked for retry purposes. For a populated array, we are looking for where the numeric status matches
    and the code from the exception appears in the array. As an example:

    .. code-block:: python

        {
            400: ['QuotaExceeded'],
            500: []
        }

    If no configuration is provided, then the default for service errors is to retry on HTTP 409/IncorrectState, 429's and 5xx's (except 501) without any
    code checks. If a specific 5xx code (e.g. 500, 502) is provided in the dictionary, then it takes precedence over the option to retry on any 500, for example,
    it is possible to retry on only 502s (either by status or by status and matching some code) by disabling the general "retry on any 5xx"
    configuration and placing an entry for 502 in the dictionary
    """

    RETRYABLE_STATUSES_AND_CODES = {
        -1: [],
        409: ['IncorrectState'],
        429: []
    }

    def __init__(self, service_error_retry_config=RETRYABLE_STATUSES_AND_CODES, retry_any_5xx=True, **kwargs):
        super(TimeoutConnectionAndServiceErrorRetryChecker, self).__init__(**kwargs)
        self.retry_any_5xx = retry_any_5xx
        self.service_error_retry_config = service_error_retry_config

    def should_retry(self, exception=None, response=None, **kwargs):
        if isinstance(exception, Timeout):
            return True
        elif isinstance(exception, RequestsConnectionError):
            return True
        elif isinstance(exception, RequestException):
            return True
        elif isinstance(exception, ConnectTimeout):
            return True
        elif isinstance(exception, CircuitBreakerError):
            if 'circuit_breaker_callback' in kwargs:
                threading.Thread(target=kwargs['circuit_breaker_callback'], args=(exception,)).start()
            return True
        elif isinstance(exception, ServiceError):
            if exception.status in self.service_error_retry_config:
                codes = self.service_error_retry_config[exception.status]
                if not codes:
                    return True
                else:
                    return exception.code in codes
            elif self.retry_any_5xx and exception.status >= 500 and exception.status != 501:
                return True
        else:
            # This is inside a try block because ConnectionError exists in Python 3 and not in Python 2
            try:
                if isinstance(exception, ConnectionError):
                    return True
            except NameError:
                pass

        return False
