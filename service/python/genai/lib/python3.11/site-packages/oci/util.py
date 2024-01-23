# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import absolute_import

import base64
import datetime
import json
import re
import os
import os.path

import pytz

from oci._vendor import six
import oci.exceptions

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from io import SEEK_SET
import logging

logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)
INSTANCE_PRINCIPAL_AUTHENTICATION_TYPE_VALUE_NAME = 'instance_principal'
DELEGATION_TOKEN_WITH_INSTANCE_PRINCIPAL_AUTHENTICATION_TYPE = 'delegation_token_with_instance_principal'
RESOURCE_PRINCIPAL_AUTHENTICATION_TYPE = 'resource_principal'
DELEGATION_TOKEN_FILE_FIELD_NAME = 'delegation_token_file'
AUTHENTICATION_TYPE_FIELD_NAME = 'authentication_type'
MEBIBYTE = 1024 * 1024
DEFAULT_BUFFER_SIZE = 100 * MEBIBYTE
DEFAULT_PART_SIZE = 128 * MEBIBYTE

try:
    # PY3+
    import collections.abc as abc
except ImportError:
    # PY2
    import collections as abc

missing_attr = object()


def to_dict(obj):
    """Helper to flatten models into dicts for rendering.

    The following conversions are applied:

    * datetime.date, datetime.datetime, datetime.time
      are converted into ISO8601 UTC strings
    """
    # Shortcut strings so they don't count as Iterables
    if isinstance(obj, six.string_types):
        return obj
    elif obj is NONE_SENTINEL:
        return None
    elif isinstance(obj, (datetime.datetime, datetime.time)):
        # always use UTC
        if not obj.tzinfo:
            obj = pytz.utc.localize(obj)
        if isinstance(obj, datetime.datetime):
            # only datetime.datetime takes a separator
            return obj.isoformat(sep="T")
        return obj.isoformat()
    elif isinstance(obj, datetime.date):
        # datetime.date doesn't have a timezone
        return obj.isoformat()
    elif isinstance(obj, abc.Mapping):
        return {k: to_dict(v) for k, v in six.iteritems(obj)}
    elif isinstance(obj, abc.Iterable):
        return [to_dict(v) for v in obj]
    # Not a string, datetime, dict, list, or model - return directly
    elif not hasattr(obj, "swagger_types"):
        return obj

    # Collect attrs from obj according to swagger_types into a dict
    as_dict = {}
    for key in six.iterkeys(obj.swagger_types):
        value = getattr(obj, key, missing_attr)
        if value is not missing_attr:
            as_dict[key] = to_dict(value)
    return as_dict


def formatted_flat_dict(model):
    """Returns a string of the model flattened as a dict, sorted"""
    as_dict = to_dict(model)
    return json.dumps(
        as_dict,
        indent=2,
        sort_keys=True
    )


def value_allowed_none_or_none_sentinel(value_to_test, allowed_values):
    return value_to_test is None or value_to_test is NONE_SENTINEL or value_to_test in allowed_values


def file_content_as_launch_instance_user_data(file_path):
    """
    Takes a file path and returns a Base64-encoded string which can be provided as the value of the ``user_data`` key
    in the ``metadata`` dictionary when launching an instance(see :py:class:`~oci.core.models.LaunchInstanceDetails`
    for more information).

    :param str file_path:
      The path to the file whose contents will be Base64-encoded

    :return: The Base64-encoded string
    :rtype: str
    """

    full_path = os.path.expandvars(os.path.expanduser(file_path))
    with open(full_path, 'rb') as f:
        file_contents = f.read()

    return base64.b64encode(file_contents).decode('utf-8')


class Sentinel(object):
    """Named singletons for clear docstrings.
    Also used to differentiate an explicit param of None from a lack of argument.

    .. code-block:: pycon

        >>> missing = Sentinel("Missing", False)
        >>> also_missing = Sentinel("Missing", False)
        >>> assert missing is also_missing
        >>> repr(missing)
        <Missing>
        >>> assert bool(missing) is False
    """
    _symbols = {}

    def __new__(cls, name, truthy=True):
        sentinel = Sentinel._symbols.get(name, None)
        if sentinel is None:
            sentinel = Sentinel._symbols[name] = super(Sentinel, cls).__new__(cls)
        elif sentinel.truthy is not truthy:
            raise ValueError("Tried to get existing Sentinel {!r} with wrong truthy value".format(sentinel))
        return sentinel

    def __init__(self, name, truthy=True):
        self.name = name
        self.truthy = truthy

    def __repr__(self):
        # Sentinel("Missing") -> <Missing>
        return "<{}>".format(self.name)

    def __bool__(self):
        return self.truthy
    # PY2 Compatibility
    __nonzero__ = __bool__


NONE_SENTINEL = Sentinel(name='None', truthy=False)

WAIT_RESOURCE_NOT_FOUND = Sentinel(name='WaitResourceNotFound', truthy=False)


def _get_signer_from_delegation_token_instance_principal(config):
    # Import the signer inside the function to avoid circular imports during initialization
    from oci.auth.signers import InstancePrincipalsDelegationTokenSigner

    signer_kwargs = {}

    delegation_token_file_path = config.get(DELEGATION_TOKEN_FILE_FIELD_NAME)

    if delegation_token_file_path is None:
        raise oci.exceptions.InvalidConfig('ERROR: {} was not provided.'.format(DELEGATION_TOKEN_FILE_FIELD_NAME))

    expanded_delegation_token_file_path = os.path.expanduser(delegation_token_file_path)
    if not os.path.isfile(expanded_delegation_token_file_path):
        raise oci.exceptions.InvalidConfig('ERROR: delegation token file not found at {}'.format(expanded_delegation_token_file_path))

    with open(expanded_delegation_token_file_path, mode="r") as f:
        delegation_token = f.read().strip()
    if delegation_token is None:
        raise oci.exceptions.InvalidConfig('ERROR: delegation_token was not provided.')
    signer_kwargs['delegation_token'] = delegation_token
    # Return signer with delegation token
    return InstancePrincipalsDelegationTokenSigner(**signer_kwargs)


def _get_signer_from_resource_principal(config):
    # Import the signer inside the function to avoid circular imports during initialization
    from oci.auth.signers import get_resource_principal_signer

    return get_resource_principal_signer()


# This map can be easily extended to accommodate support for more auth types through the config file
AUTH_TYPE_TO_SIGNER_FUNCTION_MAP = {
    DELEGATION_TOKEN_WITH_INSTANCE_PRINCIPAL_AUTHENTICATION_TYPE: _get_signer_from_delegation_token_instance_principal,
    RESOURCE_PRINCIPAL_AUTHENTICATION_TYPE: _get_signer_from_resource_principal,
}


def get_signer_from_authentication_type(config):
    # This is currently made for allowing SDK to run seamlessly on cloud shell
    auth_type = get_authentication_type_from_config(config)

    # Get the signer function from map
    signer_function = AUTH_TYPE_TO_SIGNER_FUNCTION_MAP.get(auth_type)
    return signer_function(config)


def get_authentication_type_from_config(config):
    auth_type = config.get(AUTHENTICATION_TYPE_FIELD_NAME)
    if auth_type is None:
        raise ValueError("{} not provided".format(AUTHENTICATION_TYPE_FIELD_NAME))

    # Currently the SDK supports only the cloud shell use case, this can be extended for other auth types
    if auth_type == INSTANCE_PRINCIPAL_AUTHENTICATION_TYPE_VALUE_NAME:
        if DELEGATION_TOKEN_FILE_FIELD_NAME in config:
            return DELEGATION_TOKEN_WITH_INSTANCE_PRINCIPAL_AUTHENTICATION_TYPE
        else:
            raise oci.exceptions.InvalidConfig("The authentication type {} requires config values for the keys {}".format(DELEGATION_TOKEN_WITH_INSTANCE_PRINCIPAL_AUTHENTICATION_TYPE, DELEGATION_TOKEN_FILE_FIELD_NAME))
    else:
        raise oci.exceptions.InvalidConfig("The authentication type {} is not supported".format(auth_type))


def back_up_body_calculate_stream_content_length(stream, buffer_limit=DEFAULT_BUFFER_SIZE):
    # Note: Need to read in chunks, older version of Python will fail to read more than 2GB at once.
    # We pull data in chunks (128MB at a time) from the stream until there is no more
    logger.warning("Reading the stream to calculate its content-length. Process may freeze for very big streams. Consider passing in content length for big objects")
    try:
        keep_reading = True
        part_size = DEFAULT_PART_SIZE
        content_length = 0
        content = ""
        byte_content = b''
        while keep_reading:
            if hasattr(stream, 'buffer'):
                content = stream.buffer.read(part_size)
            elif hasattr(stream, 'read'):
                content = stream.read(part_size)
            else:
                raise TypeError("Stream object does not contain a 'read' property. Cannot auto calculate content length, please pass in content length")
            if len(content) == 0:
                keep_reading = False
            byte_content += content
            content_length += len(content)
            if (buffer_limit and content_length > buffer_limit):
                raise BufferError("Stream size is greater than the buffer_limit, please pass in a bigger buffer_limit or pass in content length to the request")
        return {"content_length": content_length, "byte_content": byte_content}
    except (IOError, OSError):
        raise TypeError("Stream object's content length cannot be calculated, please pass in content length")


# This helper function checks if an object can have it's content length auto-calculated by the Request library
def is_content_length_calculable_by_req_util(o):
    if hasattr(o, '__len__') or hasattr(o, 'len') or hasattr(o, 'fileno') or hasattr(o, 'tell'):
        return True
    logger.warning("Request did not contain content-length and stream object does not contain fileno or tell property. Stream object will be read to calculate content-length")
    return False


def extract_service_endpoint(endpoint_with_base_path):
    """
    Takes a Service Endpoint with base-path embedded and extracts the Service Endpoint from it.

    :param str endpoint_with_base_path:
    Service Endpoint with base-path embedded

    :return: The Service Endpoint without base-path.
    :rtype: str
    """
    parsed_endpoint = urlparse(endpoint_with_base_path)
    return parsed_endpoint.scheme + r'://' + parsed_endpoint.netloc


def should_record_body_position_for_retry(func_ref, **func_kwargs):
    func_name = func_ref.__name__
    # TODO: remove Python 2 requirements, use qualname
    if func_name == 'call_api':
        body = func_kwargs.get('body')
        # A file-like object body should be treated differently for retry
        if body and hasattr(body, 'read'):
            return True
        return False
    return False


def record_body_position_for_rewind(body):
    is_body_rewindable = True
    if getattr(body, 'tell', None) is not None:
        try:
            # Attempt to record current body position
            body_position = body.tell()
        except (IOError, OSError):
            # If we cannot record the current body position for a file-like body, then we should not retry
            is_body_rewindable = False
            body_position = None
            logger.warning("Unable to record body position for rewinding. This request will not be retried/rewound")
    else:
        # If the body does not support tell, then don't retry
        is_body_rewindable = False
        body_position = None
        logger.warning("Unable to record body position for rewinding. This request will not be retried/rewound")
    return is_body_rewindable, body_position


def rewind_body(body, body_position):
    if getattr(body, 'seek', None) is not None:
        try:
            body.seek(body_position, SEEK_SET)
        except (IOError, OSError):
            # If we're unable to reset the body position, then we should not retry
            logger.warning("Unable to reset body position for rewinding. This request will not be retried/rewound")
            return False
        return True
    # if the body does not support seek, then we should not retry
    logger.warning("Unable to reset body position for rewinding. This request will not be retried/rewound")
    return False


def read_stream_for_signing(signing_algorithm, body):
    bytes_read = 0
    try:
        while True:
            chunk = ""
            if hasattr(body, "read"):
                chunk = body.read(DEFAULT_PART_SIZE)
            elif hasattr(body, "buffer"):
                chunk = body.buffer.read(DEFAULT_PART_SIZE)
            if len(chunk) == 0:
                break
            bytes_read += len(chunk)
            signing_algorithm.update(chunk)
    except (IOError, OSError):
        logger.warning("Unable to read stream body for signing")
        bytes_read = -1
    return bytes_read


def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def camel_to_snake_keys(dictionary):
    outdict = {}
    for k, v in dictionary.items():
        outdict[camel_to_snake(k)] = v
    return outdict
