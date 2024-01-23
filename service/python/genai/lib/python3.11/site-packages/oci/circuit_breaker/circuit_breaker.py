# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

# Contains classes for defining and building circuit breaker strategies.
import logging
from oci.exceptions import TransientServiceError

logger = logging.getLogger(__name__)

DEFAULT_CIRCUIT_BREAKER_FAILURE_STATUSES_AND_CODES = {
    409: ['IncorrectState'],
    429: [],
    500: [],
    502: [],
    503: [],
    504: []
}


class CircuitBreakerStrategy(object):
    """
        A class which can build a circuit breaker strategy based on provided criteria.

        This builder is intended as a convenience, but callers are also able to bypass this and construct
        circuit breaker strategies directly.

        :param int failure_threshold: (optional)
            The failure_threshold parameter specifies the number of subsequent failures that causes to circuit breaker
            to move from CLOSED to OPEN state. This parameter takes an integer value with 10 being the default value.

        :param int recovery_timeout: (optional)
            The recovery timeout is the time in seconds that the circuit breaker waits till it moves from an
            OPEN to HALF-OPEN state. This parameter takes in an integer with 30 seconds being the default value.

        :param dict failure_statuses_and_codes: (optional)
            This parameter takes in a dict object of type (int, list(str)) which consist of
            the status code and the list of error codes the circuit breaker takes in account for failure threshold.
            If the list of error code is an empty list the circuit breaker would mark all errors as failure which has
            that specific status code regardless of the error code.

            defaults to:
            {
                409: ['IncorrectState'],
                429: [],
                500: [],
                502: [],
                503: [],
                504: []
            }

        :param str name: (optional)
            The name of Circuit Breaker. Each circuit breaker instance is by internally made unique to a client. This
            makes sure that a circuit breaker of one client does not interfere with the operations of the other clients,
            even if they belong to the same service. In a rare case, when it is intended to share the same Circuit Breaker
            across multiple clients, a CircuitBreakerStrategy object can be made with the name value set as desired
            and passed to the clients meant to share the circuit breaker. In this scenario failures from any client
            add to the failure threshold of the circuit breaker shared by all clients.
    """

    def __init__(self, **kwargs):
        """
            Creates a new builder and initializes it based on any provided parameters.
        """
        self.failure_threshold = kwargs.get('failure_threshold', 10)
        self.recovery_timeout = kwargs.get('recovery_timeout', 30)
        self.expected_exception = TransientServiceError
        self.failure_statuses_and_codes = kwargs.get('failure_statuses_and_codes',
                                                     DEFAULT_CIRCUIT_BREAKER_FAILURE_STATUSES_AND_CODES)
        self.name = kwargs.get('name', None)

    def is_transient_error(self, status_code, service_code):
        logger.debug('Is transient error status code:{} error code:{}'.format(status_code, service_code))
        if status_code in self.failure_statuses_and_codes:
            error_code = self.failure_statuses_and_codes[status_code]
            if not error_code:
                return True
            return service_code in error_code
        logger.debug(
            'status code:{} not in failure_statuses_and_codes:{}'.format(status_code, self.failure_statuses_and_codes))
        return False


class NoCircuitBreakerStrategy(object):
    """
           A class which represents that no circuit breaker strategy is to be used for the Client.
    """

    def __init__(self):
        pass
