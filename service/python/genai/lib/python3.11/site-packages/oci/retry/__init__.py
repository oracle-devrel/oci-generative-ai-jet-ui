# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .retry import BACKOFF_FULL_JITTER_VALUE, BACKOFF_EQUAL_JITTER_VALUE, BACKOFF_FULL_JITTER_EQUAL_ON_THROTTLE_VALUE, \
    BACKOFF_DECORRELATED_JITTER_VALUE
from .retry import RetryStrategyBuilder, NoneRetryStrategy, ExponentialBackoffRetryStrategyBase, \
    ExponentialBackoffWithFullJitterRetryStrategy, ExponentialBackoffWithEqualJitterRetryStrategy, \
    ExponentialBackoffWithFullJitterEqualForThrottlesRetryStrategy, \
    ExponentialBackOffWithDecorrelatedJitterRetryStrategy
from . import retry_checkers
import os

#: A retry strategy which has all options enabled and which will use the default settings for those options. These
#: defaults are:
#:
#: * 8 total attempts - 1 original and 7 retries
#: * Total allowed elapsed time for all requests of 600 seconds (10 minutes)
#: * Exponential backoff with jitter using a base time of 1 second and an exponent of 2
#: * The maximum wait time between calls is 30 seconds
#: * Exponential backoff with de-correlated jitter of 1000 milliseconds is used
#: * Retries on the following exception types:-
#:
#:      - timeouts and connection errors
#:      - HTTP 409/IncorrectState, 429s (throttles)
#:      - Any HTTP 5xx except 501
DEFAULT_RETRY_STRATEGY = RetryStrategyBuilder().add_max_attempts(max_attempts=8) \
    .add_total_elapsed_time(total_elapsed_time_seconds=600) \
    .add_service_error_check(service_error_retry_config=retry_checkers.RETRYABLE_STATUSES_AND_CODES,
                             service_error_retry_on_any_5xx=True) \
    .get_retry_strategy()

#: A retry strategy which can be set by the user to modify the SDK retry behavior globally. Initially set to ``None``, users
#: can pass to it a Retry Strategy which can be:-
#:
#: * A retry strategy built using ``oci.retry.RetryStrategyBuilder``
#: * The ``oci.retry.DEFAULT_RETRY_STRATEGY``
#: * ``oci.retry.NoneRetryStrategy()`` which will disable retries at SDK level
#:
#: A helpful environment variable ``OCI_SDK_DEFAULT_RETRY_ENABLED`` is also provided to `enable/disable` default retries for the SDK
#:
GLOBAL_RETRY_STRATEGY = None
if 'OCI_SDK_DEFAULT_RETRY_ENABLED' in os.environ:
    if os.environ.get('OCI_SDK_DEFAULT_RETRY_ENABLED').lower() == 'true':
        GLOBAL_RETRY_STRATEGY = DEFAULT_RETRY_STRATEGY
    else:
        GLOBAL_RETRY_STRATEGY = NoneRetryStrategy()

__all__ = [
    "retry_checkers", "RetryStrategyBuilder", "NoneRetryStrategy", "ExponentialBackoffRetryStrategyBase",
    "ExponentialBackoffWithFullJitterRetryStrategy", "ExponentialBackoffWithEqualJitterRetryStrategy",
    "ExponentialBackoffWithFullJitterEqualForThrottlesRetryStrategy",
    "ExponentialBackOffWithDecorrelatedJitterRetryStrategy", "DEFAULT_RETRY_STRATEGY", "GLOBAL_RETRY_STRATEGY",
    "BACKOFF_FULL_JITTER_VALUE", "BACKOFF_EQUAL_JITTER_VALUE", "BACKOFF_FULL_JITTER_EQUAL_ON_THROTTLE_VALUE",
    "BACKOFF_DECORRELATED_JITTER_VALUE"
]
