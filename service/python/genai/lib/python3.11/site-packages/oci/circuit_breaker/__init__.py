# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .circuit_breaker import CircuitBreakerStrategy, NoCircuitBreakerStrategy, DEFAULT_CIRCUIT_BREAKER_FAILURE_STATUSES_AND_CODES
import os
import logging

#: Default Circuit Breaker Strategy provided for convenience which has the following values configured by default.
#: Detailed information on Circuit Breakers and their configuration can be found at the
#: link (https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/sdk_behaviors/circuit_breakers.html)
#:
#: * failure_threshold - 10
#: * recovery_timeout - 30 seconds
#: * failure_statuses_and_codes
#:
#:    - HTTP 409/IncorrectState
#:    - HTTP 429
#:    - HTTP 500
#:    - HTTP 502
#:    - HTTP 503
#:    - HTTP 504
#:
DEFAULT_CIRCUIT_BREAKER_STRATEGY = CircuitBreakerStrategy()

logger = logging.getLogger(name=__name__)

#: A Circuit Breaker strategy which can be set by the user to modify the SDK retry behavior globally. Initially set to ``None``, users
#: can pass to it a Circuit Breaker Strategy which can be:-
#:
#: * A Circuit Breaker Strategy built using ``oci.circuit_breaker.CircuitBreakerStrategy`` class
#: * The ``oci.circuit_breaker.DEFAULT_CIRCUIT_BREAKER_STRATEGY``
#: * ``oci.circuit_breaker.NoCircuitBreakerStrategy()`` which will disable Circuit Breaker at SDK level
#:
#: A helpful environment variable OCI_SDK_DEFAULT_CIRCUITBREAKER_ENABLED is also provided to enable/disable default circuit breakers for the SDK
#:
GLOBAL_CIRCUIT_BREAKER_STRATEGY = None
if 'OCI_SDK_DEFAULT_CIRCUITBREAKER_ENABLED' in os.environ:
    if os.environ.get('OCI_SDK_DEFAULT_CIRCUITBREAKER_ENABLED').lower() == 'true':
        logger.info('Default Circuit breaker strategy enabled')
        GLOBAL_CIRCUIT_BREAKER_STRATEGY = DEFAULT_CIRCUIT_BREAKER_STRATEGY
    else:
        logger.info('Default Circuit breaker strategy disabled')
        GLOBAL_CIRCUIT_BREAKER_STRATEGY = NoCircuitBreakerStrategy()

__all__ = ["CircuitBreakerStrategy", "NoCircuitBreakerStrategy", "DEFAULT_CIRCUIT_BREAKER_STRATEGY",
           "GLOBAL_CIRCUIT_BREAKER_STRATEGY", "DEFAULT_CIRCUIT_BREAKER_FAILURE_STATUSES_AND_CODES"]
