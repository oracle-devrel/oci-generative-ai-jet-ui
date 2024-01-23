# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import absolute_import
import json
import logging
import platform

import circuitbreaker
import pytz
import random
import os
import re
import string
import uuid
import copy
# This was added to address thread safety issues with datetime.strptime
# See https://bugs.python.org/issue7980.
import _strptime  # noqa: F401
from datetime import date, datetime, timezone
from timeit import default_timer as timer
from ._vendor import requests, six, urllib3
from dateutil.parser import parse
from dateutil import tz

import functools
from six.moves.http_client import HTTPResponse

from . import constants, exceptions, regions, retry
from .auth import signers
from .config import get_config_value_or_default, validate_config
from .request import Request
from .response import Response
from .circuit_breaker import CircuitBreakerStrategy, NoCircuitBreakerStrategy
from circuitbreaker import CircuitBreaker, CircuitBreakerMonitor
from .version import __version__
from .util import NONE_SENTINEL, Sentinel, extract_service_endpoint
missing = Sentinel("Missing")
APPEND_USER_AGENT_ENV_VAR_NAME = "OCI_SDK_APPEND_USER_AGENT"
OCI_REALM_SPECIFIC_SERVICE_ENDPOINT_TEMPLATE_ENABLED = "OCI_REALM_SPECIFIC_SERVICE_ENDPOINT_TEMPLATE_ENABLED"
APPEND_USER_AGENT = os.environ.get(APPEND_USER_AGENT_ENV_VAR_NAME)
USER_INFO = "Oracle-PythonSDK/{}".format(__version__)

DICT_VALUE_TYPE_REGEX = re.compile(r'dict\(str, (.+?)\)$')  # noqa: W605
LIST_ITEM_TYPE_REGEX = re.compile(r'list\[(.+?)\]$')  # noqa: W605
TROUBLESHOOT_URL = 'https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdk_troubleshooting.htm'

# Expect header is enabled by default
enable_expect_header = True
expect_header_env_var = os.environ.get('OCI_PYSDK_USING_EXPECT_HEADER', True)
if isinstance(expect_header_env_var, six.string_types) and expect_header_env_var.lower() == "false":
    enable_expect_header = False


def merge_type_mappings(*dictionaries):
    merged = {}
    for dictionary in dictionaries:
        merged.update(dictionary)
    return merged


def build_user_agent(extra=""):
    agent = "{} (python {}; {}-{}) {}".format(
        USER_INFO,
        platform.python_version(),
        platform.machine(),
        platform.system(),
        (extra or "")
    )
    agent = agent.strip()
    if APPEND_USER_AGENT:
        agent += " {}".format(APPEND_USER_AGENT)
    return agent


def utc_now():
    return " " + str(datetime.utcnow()) + ": "


def is_http_log_enabled(is_enabled):
    if is_enabled:
        six.moves.http_client.HTTPConnection.debuglevel = 1
    else:
        six.moves.http_client.HTTPConnection.debuglevel = 0


def _sanitize_headers_for_requests(headers):
    # Requests does not accept int or float values headers
    # Convert int, float and bool to string
    # Bools are automatically handled with this as bool is a subclass of int
    for header_name, header_value in six.iteritems(headers):
        if isinstance(header_value, six.integer_types) or isinstance(header_value, float):
            headers[header_name] = str(header_value)
    return headers


STREAM_RESPONSE_TYPE = 'stream'
BYTES_RESPONSE_TYPE = 'bytes'

# Default timeout value(second)
DEFAULT_CONNECTION_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 60.0

# The keys here correspond to the Swagger collection format values described here: https://swagger.io/docs/specification/2-0/describing-parameters/
# and the values represent delimiters we'll use between values of the collection when placing those values in the query string.
#
# Note that the 'multi' type has no delimiter since in the query string we'll want to repeat the same query string param key but
# with different values each time (e.g. myKey=val1&myKey=val2), whereas for the other types we will only pass in a single
# key=value in the query string, where the "value" is the members of the collecction with a given delimiter.
VALID_COLLECTION_FORMAT_TYPES = {
    'multi': None,
    'csv': ',',
    'tsv': '\t',
    'ssv': ' ',
    'pipes': '|'
}


def _read_all_headers(fp):
    current = None
    while current != b'\r\n':
        current = fp.readline()


def _to_bytes(input_buffer):
    bytes_buffer = []
    for chunk in input_buffer:
        if isinstance(chunk, six.text_type):
            bytes_buffer.append(chunk.encode('utf-8'))
        else:
            bytes_buffer.append(chunk)
    msg = b"\r\n".join(bytes_buffer)
    return msg


def _is_100_continue(line):
    parts = line.split(None, 2)
    return (
        len(parts) >= 3 and parts[0].startswith(b'HTTP/') and
        parts[1] == b'100')


class OCIHTTPResponse(HTTPResponse):

    def __init__(self, *args, **kwargs):
        self._status_tuple = kwargs.pop('status_tuple')
        HTTPResponse.__init__(self, *args, **kwargs)

    def _read_status(self):
        if self._status_tuple is not None:
            status_tuple = self._status_tuple
            self._status_tuple = None
            return status_tuple
        else:
            return HTTPResponse._read_status(self)


class OCIConnection(urllib3.connection.VerifiedHTTPSConnection):
    """ HTTPConnection with 100 Continue support. """

    def __init__(self, *args, **kwargs):
        super(OCIConnection, self).__init__(*args, **kwargs)
        self._original_response_cls = self.response_class
        self._response_received = False
        self._using_expect_header = False
        self.logger = logging.getLogger("{}.{}".format(__name__, id(self)))

    def _send_request(self, method, url, body, headers, *args, **kwargs):
        self._response_received = False
        if headers.get('expect', '') == '100-continue':
            if self.debuglevel > 0:
                print('Using Expect header...')
            self._using_expect_header = True
        else:
            if self.debuglevel > 0:
                print('Not using Expect header...')
            self._using_expect_header = False
            self.response_class = self._original_response_cls
        rval = super(OCIConnection, self)._send_request(
            method, url, body, headers, *args, **kwargs)
        self._expect_header_set = False
        return rval

    def _send_output(self, message_body=None, *args, **kwargs):
        self._buffer.extend((b"", b""))
        msg = _to_bytes(self._buffer)
        del self._buffer[:]

        if not self._using_expect_header:
            if isinstance(message_body, bytes):
                msg += message_body
                message_body = None

        self.send(msg)

        if self._using_expect_header:
            if self.debuglevel > 0:
                print('Waiting 3 seconds for 100-continue response...')
            if urllib3.util.wait_for_read(self.sock, 3):
                self._handle_expect_response(message_body)
                return

        if message_body is not None:
            if self.debuglevel > 0:
                print('Timeout waiting for 100-continue response, sending message body...')
            self.send(message_body)

    def _handle_expect_response(self, message_body):
        fp = self.sock.makefile('rb', 0)
        try:
            line = fp.readline()
            parts = line.split(None, 2)
            if self.debuglevel > 0:
                print(line)
            if _is_100_continue(line):
                if self.debuglevel > 0:
                    print('Received 100-continue response, sending message body...')
                _read_all_headers(fp)
                self._send_message_body(message_body)
            elif len(parts) == 3 and parts[0].startswith(b'HTTP/'):
                if self.debuglevel > 0:
                    print('Received non-100-continue response, abort request...')
                status_tuple = (parts[0].decode('ascii'),
                                int(parts[1]), parts[2].decode('ascii'))
                response_class = functools.partial(
                    OCIHTTPResponse, status_tuple=status_tuple)
                self.response_class = response_class
                self._response_received = True
        finally:
            fp.close()

    def _send_message_body(self, message_body):
        if message_body is not None:
            self.send(message_body)

    def send(self, str):
        if self._response_received:
            return
        return super(OCIConnection, self).send(str)


class OCIConnectionPool(urllib3.HTTPSConnectionPool):
    ConnectionCls = OCIConnection
    """ HTTPConnectionPool with 100 Continue support. """


# Replace the HTTPS connection pool with OCIConnectionPool once the env var `OCI_PYSDK_USING_EXPECT_HEADER` is not set
# to "FALSE"
if enable_expect_header:
    urllib3.poolmanager.pool_classes_by_scheme["https"] = OCIConnectionPool


class BaseClient(object):
    primitive_type_map = {
        'int': int,
        'float': float,
        'str': six.u,
        'bool': bool,
        'date': date,
        'datetime': datetime,
        "object": object
    }

    ALLOW_CONTROL_CHARACTERS = False

    def __init__(self, service, config, signer, type_mapping, **kwargs):
        validate_config(config, signer=signer)
        self.signer = signer

        self.config = config
        # Default to true (is a regional client) if there is nothing explicitly set. Regional
        # clients allow us to call set_region and that'll also set the endpoint. For non-regional
        # clients we require an endpoint
        self.regional_client = kwargs.get('regional_client', True)

        self._endpoint = None
        self._base_path = kwargs.get('base_path')
        self.service_endpoint_template = kwargs.get('service_endpoint_template')
        self.service_endpoint_template_per_realm = kwargs.get('service_endpoint_template_per_realm')
        self.endpoint_service_name = kwargs.get('endpoint_service_name')

        # By default self._allow_control_chars will be None. The user would need to explicitly set it to True or False
        self._allow_control_chars = kwargs.get('allow_control_chars')

        self._client_level_realm_specific_endpoint_template_enabled = kwargs.get('client_level_realm_specific_endpoint_template_enabled')  # default this to None as it should be an opt-in feature

        if self.regional_client:
            if kwargs.get('service_endpoint'):
                self.endpoint = kwargs.get('service_endpoint')
            else:
                region_to_use = None
                if 'region' in config and config['region']:
                    region_to_use = config.get('region')
                elif hasattr(signer, 'region'):
                    region_to_use = signer.region

                endpoint_template = self.handle_service_endpoint_template(region_to_use, self.service_endpoint_template, self.service_endpoint_template_per_realm)

                self.endpoint = regions.endpoint_for(
                    service,
                    service_endpoint_template=endpoint_template,
                    region=region_to_use,
                    endpoint=config.get('endpoint'),
                    endpoint_service_name=self.endpoint_service_name)
        else:
            if not kwargs.get('service_endpoint'):
                raise exceptions.MissingEndpointForNonRegionalServiceClientError('An endpoint must be provided for a non-regional service client')
            self.endpoint = kwargs.get('service_endpoint')

        self.service = service
        self.complex_type_mappings = type_mapping
        self.type_mappings = merge_type_mappings(self.primitive_type_map, type_mapping)
        self.session = requests.Session()

        # If the user doesn't specify timeout explicitly we would use default timeout.
        self.timeout = kwargs.get('timeout') if 'timeout' in kwargs else (DEFAULT_CONNECTION_TIMEOUT, DEFAULT_READ_TIMEOUT)

        self.user_agent = build_user_agent(get_config_value_or_default(config, "additional_user_agent"))

        self.logger = logging.getLogger("{}.{}".format(__name__, id(self)))
        self.logger.addHandler(logging.NullHandler())
        if get_config_value_or_default(config, "log_requests"):
            self.logger.disabled = False
            self.logger.setLevel(logging.DEBUG)
            is_http_log_enabled(True)
        else:
            self.logger.disabled = True
            is_http_log_enabled(False)

        self.skip_deserialization = kwargs.get('skip_deserialization')

        # Circuit Breaker at client level
        self.circuit_breaker_strategy = kwargs.get('circuit_breaker_strategy')
        self.circuit_breaker_name = None
        # Log if Circuit Breaker Strategy is not enabled or if using Default Circuit breaker Strategy
        if self.circuit_breaker_strategy is None or isinstance(self.circuit_breaker_strategy, NoCircuitBreakerStrategy):
            self.logger.debug('No circuit breaker strategy enabled!')
        else:
            # Enable Circuit breaker if a valid circuit breaker strategy is available
            if not isinstance(self.circuit_breaker_strategy, CircuitBreakerStrategy):
                raise TypeError('Invalid Circuit Breaker Strategy!')
            self.circuit_breaker_name = str(uuid.uuid4()) if self.circuit_breaker_strategy.name is None else self.circuit_breaker_strategy.name
            # Re-use Circuit breaker if sharing a Circuit Breaker Strategy.
            circuit_breaker = CircuitBreakerMonitor.get(self.circuit_breaker_name)
            if circuit_breaker is None:
                circuit_breaker = CircuitBreaker(
                    failure_threshold=self.circuit_breaker_strategy.failure_threshold,
                    recovery_timeout=self.circuit_breaker_strategy.recovery_timeout,
                    expected_exception=self.circuit_breaker_strategy.expected_exception,
                    name=self.circuit_breaker_name
                )
            # Equivalent to decorating the request function with Circuit Breaker
            self.request = circuit_breaker(self.request)
        self.logger.debug('Endpoint: {}'.format(self._endpoint))

    def handle_service_endpoint_template(self, region_id, service_endpoint_template, service_endpoint_template_per_realm):
        should_enable_realm_template = self.should_allow_template_per_realm()

        if should_enable_realm_template:
            if region_id in regions.REGION_REALMS:
                realm = regions.REGION_REALMS[region_id]
                if realm in service_endpoint_template_per_realm:
                    return service_endpoint_template_per_realm[realm]

        return service_endpoint_template

    @property
    def endpoint(self):
        return self._endpoint

    @endpoint.setter
    def endpoint(self, endpoint):
        if self._base_path == '/':
            # If it's just the root path then use the endpoint as-is
            self._endpoint = endpoint
        elif self._base_path and not (endpoint.endswith(self._base_path) or endpoint.endswith('{}/'.format(self._base_path))):
            # Account for formats like https://iaas.us-phoenix-1.oraclecloud.com/20160918 and
            # https://iaas.us-phoenix-1.oraclecloud.com/20160918/ as they should both be fine
            self._endpoint = '{}{}'.format(endpoint, self._base_path)
        else:
            self._endpoint = endpoint

    def get_endpoint(self):
        return extract_service_endpoint(self._endpoint)

    def set_region(self, region):
        if self.regional_client:
            service_endpoint_template = self.handle_service_endpoint_template(region, self.service_endpoint_template, self.service_endpoint_template_per_realm)  # check what template to use
            self.endpoint = regions.endpoint_for(self.service, service_endpoint_template=service_endpoint_template, region=region, endpoint_service_name=self.endpoint_service_name)
        else:
            raise TypeError('Setting the region is not allowed for non-regional service clients. You must instead set the endpoint')

    @property
    def allow_control_chars(self):
        return self._allow_control_chars

    @allow_control_chars.setter
    def allow_control_chars(self, bool):
        self._allow_control_chars = bool

    @property
    def client_level_realm_specific_endpoint_template_enabled(self):
        return self._client_level_realm_specific_endpoint_template_enabled

    @client_level_realm_specific_endpoint_template_enabled.setter
    def client_level_realm_specific_endpoint_template_enabled(self, bool):
        self._client_level_realm_specific_endpoint_template_enabled = bool

        # Recalculate the endpoint since service endpoint template per realm is toggled
        region_to_use = None
        if 'region' in self.config and self.config['region']:
            region_to_use = self.config.get('region')
        elif hasattr(self.signer, 'region'):
            region_to_use = self.signer.region

        service_endpoint_template = self.handle_service_endpoint_template(region_to_use, self.service_endpoint_template, self.service_endpoint_template_per_realm)

        self.endpoint = regions.endpoint_for(
            self.service,
            service_endpoint_template=service_endpoint_template,
            region=region_to_use,
            endpoint=self.config.get('endpoint'),
            endpoint_service_name=self.endpoint_service_name)

    def is_instance_principal_or_resource_principal_signer(self):
        if (isinstance(self.signer, signers.InstancePrincipalsSecurityTokenSigner) or
                isinstance(self.signer, signers.ResourcePrincipalsFederationSigner) or
                isinstance(self.signer, signers.EphemeralResourcePrincipalSigner) or
                isinstance(self.signer, signers.EphemeralResourcePrincipalV21Signer) or
                isinstance(self.signer, signers.NestedResourcePrincipals) or
                isinstance(self.signer, signers.OkeWorkloadIdentityResourcePrincipalSigner)):
            return True
        else:
            return False

    def call_api(self, resource_path, method,
                 path_params=None,
                 query_params=None,
                 header_params=None,
                 body=None,
                 response_type=None,
                 enforce_content_headers=True,
                 allow_control_chars=None,
                 operation_name=None,
                 api_reference_link=None,
                 required_arguments=[]):
        """
        Makes the HTTP request and return the deserialized data.

        :param resource_path: Path to the resource (e.g. /instance)
        :param method: HTTP method
        :param path_params: (optional) Path parameters in the url.
        :param query_params: (optional) Query parameters in the url.
        :param header_params: (optional) Request header params.
        :param body: (optional) Request body.
        :param response_type: (optional) Response data type.
        :param enforce_content_headers: (optional) Whether content headers should be added for
            PUT and POST requests when not present.  Defaults to True.
        :param allow_control_chars: (optional) Boolean that allows whether or not the response object can contain control chars
        :param operation_name: (optional) String that represents the operational name of the API call.
        :param api_reference_link: (optional) String that represents the link to the API reference page for this operation.
        :return: A Response object, or throw in the case of an error.

        """

        if header_params:
            # Remove expect header if user has disabled it, or if the operation is not PUT, POST or PATCH
            if not enable_expect_header or method.lower() not in ["put", "post", "patch"]:
                map_lowercase_header_params_keys_to_actual_keys = {k.lower(): k for k in header_params}
                if "expect" in map_lowercase_header_params_keys_to_actual_keys:
                    header_params.pop(map_lowercase_header_params_keys_to_actual_keys.get("expect"), None)

            header_params = self.sanitize_for_serialization(header_params)

        header_params = header_params or {}

        # All the headers have been prepared for serialization at this point
        header_params = _sanitize_headers_for_requests(header_params)

        header_params[constants.HEADER_CLIENT_INFO] = USER_INFO
        header_params[constants.HEADER_USER_AGENT] = self.user_agent

        if header_params.get(constants.HEADER_REQUEST_ID, missing) is missing:
            header_params[constants.HEADER_REQUEST_ID] = self.build_request_id()

        # This allows for testing with "fake" database resources.
        opc_host_serial = os.environ.get('OCI_DB_OPC_HOST_SERIAL')
        if opc_host_serial:
            header_params['opc-host-serial'] = opc_host_serial

        if path_params:
            path_params = self.sanitize_for_serialization(path_params)
            for k, v in path_params.items():
                replacement = six.moves.urllib.parse.quote(str(self.to_path_value(v)))
                resource_path = resource_path.\
                    replace('{' + k + '}', replacement)

        if query_params:
            query_params = self.process_query_params(query_params)

        if body is not None and header_params.get('content-type') == 'application/json':
            body = self.sanitize_for_serialization(body)
            body = json.dumps(body)

        # Here is where we will change our endpoint with the path / query params if a {serviceParam} exists on the endpoint
        endpoint = self.handle_service_params_in_endpoint(path_params, query_params, required_arguments)
        url = endpoint + resource_path

        request = Request(
            method=method,
            url=url,
            query_params=query_params,
            header_params=header_params,
            body=body,
            response_type=response_type,
            enforce_content_headers=enforce_content_headers
        )

        if self.is_instance_principal_or_resource_principal_signer():
            call_attempts = 0
            while call_attempts < 2:
                try:
                    return self.request(request, allow_control_chars, operation_name, api_reference_link)
                except exceptions.ServiceError as e:
                    call_attempts += 1
                    if e.status == 401 and call_attempts < 2:
                        self.signer.refresh_security_token()
                    else:
                        raise
        else:
            start = timer()
            response = self.request(request, allow_control_chars, operation_name, api_reference_link)
            end = timer()
            self.logger.debug('time elapsed for request: {}'.format(str(end - start)))
            return response

    def map_service_params_to_values(self, service_params_url, path_params, query_params, required_arguments):
        service_params_map = {}
        service_params = set(filter(None, ("".join(service_params_url.replace(".", "").split("{"))).split("}")))
        for service_param in service_params:
            should_append_dot = False
            # # Check if there is a +Dot, if so we need to append a dot after appending the service_param
            if "+Dot" in service_param:
                should_append_dot = True
                dot_idx = service_param.find("+Dot")
                service_param = service_param[0:dot_idx]  # remove the +Dot in service param

            if service_param in required_arguments and (service_param in path_params or service_param in query_params):
                value = path_params[service_param] if service_param in path_params else query_params[service_param]
                if should_append_dot:
                    value += "."
                    service_params_map[service_param + "+Dot"] = value
                else:
                    service_params_map[service_param] = value
            else:  # If service_param was not found, we do not want to include it as part of the url. Set it as an empty string value
                if should_append_dot:
                    service_params_map[service_param + "+Dot"] = ""
                else:
                    service_params_map[service_param] = ""

        return service_params_map

    def handle_service_params_in_endpoint(self, path_params, query_params, required_arguments):
        endpoint = self.endpoint
        start_idx = len("https://")
        if endpoint[start_idx] == "{":  # If the character after https:// is a "{", we have service params
            end_idx = endpoint.rfind("}")
            service_params_url = endpoint[start_idx:end_idx + 1]
            service_params_map = self.map_service_params_to_values(service_params_url, path_params, query_params, required_arguments)

            for service_param, value in service_params_map.items():
                service_param = "{" + service_param + "}"
                endpoint = endpoint.replace(service_param, value)

        return endpoint

    def generate_collection_format_param(self, param_value, collection_format_type):
        if param_value is missing:
            return missing

        if collection_format_type not in VALID_COLLECTION_FORMAT_TYPES:
            raise ValueError('Invalid collection format type {}. Valid types are: {}'.format(collection_format_type, list(VALID_COLLECTION_FORMAT_TYPES.keys())))

        if collection_format_type == 'multi':
            return param_value
        else:
            return VALID_COLLECTION_FORMAT_TYPES[collection_format_type].join(param_value)

    def process_query_params(self, query_params):
        query_params = self.sanitize_for_serialization(query_params)

        processed_query_params = {}
        for k, v in query_params.items():
            # First divide our query params into ones where the param value is "simple" (not a dict or list), a list or a dict. Since we're
            # executing after sanitize_for_serialization has been called it's dicts, lists or primitives all the way down.
            #
            # The params where the value is a dict are, for example, tags we need to handle differently for inclusion
            # in the query string.
            #
            # The params where the value is a list are multivalued parameters in the query string.
            #
            # An example query_params is:
            #
            #   {
            #       "stuff": "things",
            #       "collectionFormat": ["val1", "val2", "val3"]
            #       "dictTags": { "tag1": ["val1", "val2", "val3"], "tag2": ["val1"] },
            #       "dictTagsExists": { "tag3": True, "tag4": True }
            #   }
            #
            # And we can categorize the params as:
            #
            #   Simple: "stuff":"things"
            #   List: "collectionFormat": ["val1", "val2", "val3"]
            #   Dict: "dictTags": { "tag1": ["val1", "val2", "val3"], "tag2": ["val1"] }, "dictTagsExists": { "tag3": True, "tag4": True }
            if isinstance(v, bool):
                # Python capitalizes boolean values in the query parameters.
                processed_query_params[k] = 'true' if v else 'false'
            elif not isinstance(v, dict) and not isinstance(v, list):
                processed_query_params[k] = self.to_path_value(v)
            elif isinstance(v, list):
                # The requests library supports lists to represent multivalued params natively
                # (http://docs.python-requests.org/en/master/api/#requests.Session.params) so we just have to assign
                # the list to the key (where the key is the query string param key)
                processed_query_params[k] = v
            else:
                # If we are here then we either have:
                #
                #   1) a dict where the value is an array. The requests library supports lists to represent multivalued params
                #      natively (http://docs.python-requests.org/en/master/api/#requests.Session.params) so we just have to
                #      manipulate things into the right key. In the case of something like:
                #
                #           "dictTags": { "tag1": ["val1", "val2", "val3"], "tag2": ["val1"] }
                #
                #      What we want is to end up with:
                #
                #           "dictTags.tag1": ["val1", "val2", "val3"], "dictTags.tag2": ["val1"]
                #
                #   2) a dict where the value is not an array and in this case we just explode out the content. For example if we have:
                #
                #           "dictTagsExists": { "tag3": True, "tag4": True }
                #
                #       What we'll end up with is:
                #
                #           "dictTagsExists.tag3": True, "dictTagsExists.tag4": True
                for inner_key, inner_val in v.items():
                    processed_query_params['{}.{}'.format(k, inner_key)] = inner_val

        return processed_query_params

    def request(self, request, allow_control_chars=None, operation_name=None, api_reference_link=None):
        self.logger.info(utc_now() + "Request: %s %s" % (str(request.method), request.url))

        initial_circuit_breaker_state = None
        if self.circuit_breaker_name:
            initial_circuit_breaker_state = CircuitBreakerMonitor.get(self.circuit_breaker_name).state
            if initial_circuit_breaker_state != circuitbreaker.STATE_CLOSED:
                self.logger.debug("Circuit Breaker State is {}!".format(initial_circuit_breaker_state))

        signer = self.signer
        if not request.enforce_content_headers:
            signer = signer.without_content_headers

        stream = False
        if request.response_type == STREAM_RESPONSE_TYPE:
            stream = True

        try:
            start = timer()
            response = self.session.request(
                request.method,
                request.url,
                auth=signer,
                params=request.query_params,
                headers=request.header_params,
                data=request.body,
                stream=stream,
                timeout=self.timeout)
            end = timer()
            if request.header_params[constants.HEADER_REQUEST_ID]:
                self.logger.debug(utc_now() + 'time elapsed for request {}: {}'.format(request.header_params[constants.HEADER_REQUEST_ID], str(end - start)))
            if response and hasattr(response, 'elapsed'):
                self.logger.debug(utc_now() + "time elapsed in response: " + str(response.elapsed))
        except requests.exceptions.ConnectTimeout as e:
            if not e.args:
                e.args = ('',)
            e.args = e.args + ("Request Endpoint: " + request.method + " " + request.url + " See {} for help troubleshooting this error, or contact support and provide this full error message.".format(TROUBLESHOOT_URL),)
            raise exceptions.ConnectTimeout(e)
        except requests.exceptions.RequestException as e:
            if not e.args:
                e.args = ('',)
            e.args = e.args + ("Request Endpoint: " + request.method + " " + request.url + " See {} for help troubleshooting this error, or contact support and provide this full error message.".format(TROUBLESHOOT_URL),)
            raise exceptions.RequestException(e)

        response_type = request.response_type
        self.logger.debug(utc_now() + "Response status: %s" % str(response.status_code))

        # Raise Service Error or Transient Service Error
        if not 200 <= response.status_code <= 299:
            target_service = self.service
            request_endpoint = request.method + " " + request.url
            client_version = USER_INFO
            timestamp = datetime.now(timezone.utc).isoformat()

            service_code, message, deserialized_data = self.get_deserialized_service_code_and_message(response, allow_control_chars)
            if response.status_code == 413 and service_code == 'RequestEntityTooLarge':
                self.logger.warning("Recieved a 413/RequestEntityTooLarge from {}, resetting session".format(target_service))
                _ = response.content  # Read the response content to enable closing the socket.
                response.close()
                new_session = copy.copy(self.session)
                self.session.close()
                self.session = new_session
            if isinstance(self.circuit_breaker_strategy, CircuitBreakerStrategy) and self.circuit_breaker_strategy.is_transient_error(response.status_code, service_code):
                new_circuit_breaker_state = CircuitBreakerMonitor.get(self.circuit_breaker_name).state
                if initial_circuit_breaker_state != new_circuit_breaker_state:
                    self.logger.warning("Circuit Breaker state changed from {} to {}".format(initial_circuit_breaker_state, new_circuit_breaker_state))
                self.raise_transient_service_error(request, response, service_code, message, operation_name, api_reference_link, target_service, request_endpoint, client_version, timestamp, deserialized_data)
            else:
                self.raise_service_error(request, response, service_code, message, operation_name, api_reference_link, target_service, request_endpoint, client_version, timestamp, deserialized_data)

        if stream:
            # Don't unpack a streaming response body
            deserialized_data = response
        elif response_type == BYTES_RESPONSE_TYPE:
            # Don't deserialize data responses.
            deserialized_data = response.content
        elif response_type:
            deserialized_data = self.deserialize_response_data(response.content, response_type, allow_control_chars)
        else:
            deserialized_data = None

        resp = Response(response.status_code, response.headers, deserialized_data, request)
        self.logger.debug(utc_now() + "Response returned")
        return resp

    # Builds the client info string to be sent with each request.
    def build_request_id(self):
        return str(uuid.uuid4()).replace('-', '').upper()

    def add_opc_retry_token_if_needed(self, header_params, retry_token_length=30):
        if 'opc-retry-token' not in header_params:
            header_params['opc-retry-token'] = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(retry_token_length))

    @staticmethod
    def add_opc_client_retries_header(header_params):
        if 'opc-client-retries' not in header_params:
            header_params['opc-client-retries'] = "true"

    def to_path_value(self, obj):
        """
        Takes value and turn it into a string suitable for inclusion in
        the path, by url-encoding.

        :param obj: object or string value.

        :return string: quoted value.
        """
        if type(obj) == list:
            return ','.join(obj)
        else:
            return str(obj)

    def sanitize_for_serialization(self, obj, declared_type=None, field_name=None):
        """
        Builds a JSON POST object.

        If obj is str, int, float, bool, None, return directly.
        If obj is datetime.datetime, datetime.date
            convert to string in iso8601 format.
        If obj is list, sanitize each element in the list.
        If obj is dict, return the dict.
        If obj is swagger model, return the properties dict.

        :param obj: The data to serialize.
        :return: The serialized form of data.
        """
        types = (six.string_types, six.integer_types, float, bool, type(None))

        declared_swagger_type_to_acceptable_python_types = {
            'str': six.string_types,
            'bool': bool,
            'int': (float, six.integer_types),
            'float': (float, six.integer_types)
        }

        # if there is a declared type for this obj, then validate that obj is of that type. None types (either None or the NONE_SENTINEL) are not validated but
        # instead passed through
        if declared_type and not self.is_none_or_none_sentinel(obj):
            if declared_type.startswith('dict(') and not isinstance(obj, dict):
                self.raise_type_error_serializing_model(field_name, obj, declared_type)
            elif declared_type.startswith('list[') and not (isinstance(obj, list) or isinstance(obj, tuple)):
                self.raise_type_error_serializing_model(field_name, obj, declared_type)
            elif declared_type in self.complex_type_mappings:
                # if its supposed to be one of our models, it can either be an instance of that model OR a dict
                if not isinstance(obj, dict) and not isinstance(obj, self.complex_type_mappings[declared_type]):
                    self.raise_type_error_serializing_model(field_name, obj, declared_type)
            elif declared_type in declared_swagger_type_to_acceptable_python_types and not isinstance(obj, declared_swagger_type_to_acceptable_python_types[declared_type]):
                # if its a primitive with corresponding acceptable python types, validate that obj is an instance of one of those acceptable types
                self.raise_type_error_serializing_model(field_name, obj, declared_type)

        if isinstance(obj, types):
            return obj
        elif obj is NONE_SENTINEL:
            return None
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return [self.sanitize_for_serialization(
                sub_obj,
                self.extract_list_item_type_from_swagger_type(declared_type) if declared_type else None,
                field_name + '[*]' if field_name else None)
                for sub_obj in obj]
        elif isinstance(obj, datetime):
            if not obj.tzinfo:
                obj = pytz.utc.localize(obj)
            return obj.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        elif isinstance(obj, date):
            return obj.isoformat()
        else:
            if isinstance(obj, dict):
                obj_dict = obj

                keys_to_types_and_field_name = None

                # if there is a declared type, then we can use that to validate the types of values in the dict
                if declared_type:
                    dict_value_type = self.extract_dict_value_type_from_swagger_type(declared_type)
                    keys_to_types_and_field_name = {k: (dict_value_type, k) for k in obj_dict}
            else:
                # at this point we are assuming it is one of our models with swagger_types so explicitly throw if its not to give a better error
                if not hasattr(obj, 'swagger_types'):
                    raise TypeError('Not able to serialize data: {} of type: {} in field: {}'.format(str(obj), type(obj).__name__, field_name))

                obj_dict = {obj.attribute_map[attr]: getattr(obj, attr)
                            for attr, _ in obj.swagger_types.items()
                            if getattr(obj, attr) is not None}

                keys_to_types_and_field_name = {obj.attribute_map[attr]: (swagger_type, attr) for attr, swagger_type in six.iteritems(obj.swagger_types)}

            sanitized_dict = {}
            for key, val in six.iteritems(obj_dict):
                value_declared_type = None
                inner_field_name = key
                if keys_to_types_and_field_name:
                    value_declared_type = keys_to_types_and_field_name[key][0]
                    inner_field_name = keys_to_types_and_field_name[key][1]

                inner_field_name = '{}.{}'.format(field_name, inner_field_name) if field_name else inner_field_name
                sanitized_dict[key] = self.sanitize_for_serialization(val, value_declared_type, inner_field_name)

            return sanitized_dict

    def is_none_or_none_sentinel(self, obj):
        return (obj is None) or (obj is NONE_SENTINEL)

    def raise_type_error_serializing_model(self, field_name, obj, declared_type):
        raise TypeError('Field {} with value {} was expected to be of type {} but was of type {}'.format(field_name, str(obj), declared_type, type(obj).__name__))

    def extract_dict_value_type_from_swagger_type(self, swagger_type):
        m = DICT_VALUE_TYPE_REGEX.search(swagger_type)

        result = None
        if m:
            result = m.group(1)

        return result

    def extract_list_item_type_from_swagger_type(self, swagger_type):
        m = LIST_ITEM_TYPE_REGEX.search(swagger_type)

        result = None
        if m:
            result = m.group(1)

        return result

    def raise_service_error(self, request, response, service_code, message, operation_name=None, api_reference_link=None, target_service=None, request_endpoint=None, client_version=None, timestamp=None, deserialized_data=None):
        raise exceptions.ServiceError(
            response.status_code,
            service_code,
            response.headers,
            message,
            original_request=request,
            operation_name=operation_name,
            api_reference_link=api_reference_link,
            target_service=target_service,
            request_endpoint=request_endpoint,
            client_version=client_version,
            timestamp=timestamp,
            deserialized_data=deserialized_data)

    def raise_transient_service_error(self, request, response, service_code, message, operation_name=None, api_reference_link=None, target_service=None, request_endpoint=None, client_version=None, timestamp=None, deserialized_data=None):
        raise exceptions.TransientServiceError(
            response.status_code,
            service_code,
            response.headers,
            message,
            original_request=request,
            operation_name=operation_name,
            api_reference_link=api_reference_link,
            target_service=target_service,
            request_endpoint=request_endpoint,
            client_version=client_version,
            timestamp=timestamp,
            deserialized_data=deserialized_data)

    def get_deserialized_service_code_and_message(self, response, allow_control_chars=None):
        deserialized_data = self.deserialize_response_data(response.content, 'object', allow_control_chars)
        service_code = None
        message = None

        if isinstance(deserialized_data, dict):
            service_code = deserialized_data.get('code')
            message = deserialized_data.get('message')
        else:
            # Deserialized data should be a string if we couldn't deserialize into a dict (i.e. it failed
            # json.loads()). There could still be error information of value to the customer, so instead
            # of black holing the message, just put it in the error
            message = deserialized_data

        return service_code, message, deserialized_data

    def deserialize_response_data(self, response_data, response_type, allow_control_chars=None):
        """
        Deserializes response into an object.

        :param response_data: object to be deserialized.
        :param response_type: class literal for
            deserialized object, or string of class name.
        :param allow_control_chars: boolean to allow control character in a response. Defaults to None

        :return: deserialized object.
        """
        # response.content is always bytes
        response_data = response_data.decode('utf8')

        try:
            should_allow_control_chars = self.should_allow_control_chars(allow_control_chars)

            # Taking the inverse result because strict=True means we do not allow control characters.
            json_response = json.loads(response_data, strict=not should_allow_control_chars)
            # Load everything as JSON and then verify that the object returned
            # is a string (six.text_type) if the response type is a string.
            # This is matches the previous behavior, which happens to strip
            # the embedded quotes in the get_namespace response.
            # There is the potential that an API will declare that it returns
            # a string and the string will be a valid JSON Object. In that case
            # we do not update the response_data with the json_response.
            # If we do later steps will fail because they are expecting the
            # response_data to be a string.
            if response_type != "str" or type(json_response) == six.text_type:
                response_data = json_response
        except ValueError:
            pass

        if self.skip_deserialization:
            return response_data
        else:
            start = timer()
            res = self.__deserialize(response_data, response_type)
            end = timer()
            self.logger.debug(utc_now() + 'python SDK time elapsed for deserializing: {}'.format(str(end - start)))
            return res

    def __deserialize(self, data, cls):
        """
        Deserialize a dict, list, or str into an object.

        :param data: dict, list or str
        :param cls: string of class name

        :return: object.
        """
        if data is None:
            return None

        if cls.startswith('list['):
            sub_kls = re.match(r'list\[(.*)\]', cls).group(1)  # noqa: W605
            return [self.__deserialize(sub_data, sub_kls)
                    for sub_data in data]

        if cls.startswith('dict('):
            sub_kls = re.match(r'dict\(([^,]*), (.*)\)', cls).group(2)  # noqa: W605
            return {k: self.__deserialize(v, sub_kls)
                    for k, v in data.items()}

        # Enums are not present in type mappings, and they are strings, so we need to call  __deserialize_primitive()
        if cls in self.type_mappings:
            cls = self.type_mappings[cls]
        else:
            return self.__deserialize_primitive(data, cls)

        if hasattr(cls, 'get_subtype'):
            # Use the discriminator value to get the correct subtype.
            cls = cls.get_subtype(data)  # get_subtype returns a str
            cls = self.type_mappings[cls]

        if cls in [int, float, six.u, bool]:
            return self.__deserialize_primitive(data, cls)
        elif cls == object:
            return data
        elif cls == date:
            return self.__deserialize_date(data)
        elif cls == datetime:
            return self.__deserialize_datetime(data)
        else:
            return self.__deserialize_model(data, cls)

    def __deserialize_primitive(self, data, cls):
        """
        Deserializes string to primitive type.

        :param data: str.
        :param cls: class literal.

        :return: int, float, str, bool.
        """
        try:
            value = cls(data)
        except UnicodeEncodeError:
            value = six.u(data)
        except TypeError:
            value = data
        return value

    def __deserialize_date(self, string):
        """
        Deserializes string to date.

        :param string: str.
        :return: date.
        """
        try:
            return parse(string).date()
        except ImportError:
            return string
        except ValueError:
            raise Exception("Failed to parse `{0}` into a date object".format(string))

    def __deserialize_datetime(self, string):
        """
        Deserializes string to datetime.

        The string should be in iso8601 datetime format.

        :param string: str.
        :return: datetime.
        """
        try:
            # If this parser creates a date without raising an exception
            # then the time zone is utc and needs to be set.
            naivedatetime = datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.%fZ")
            awaredatetime = naivedatetime.replace(tzinfo=tz.tzutc())
            return awaredatetime

        except ValueError:
            try:
                return parse(string)
            except ImportError:
                return string
            except ValueError:
                raise Exception("Failed to parse `{0}` into a datetime object".format(string))
        except ImportError:
            return string

    def __deserialize_model(self, data, cls):
        """
        Deserializes list or dict to model.

        :param data: dict, list.
        :param cls: class literal.
        :return: model object.
        """
        instance = cls()

        for attr, attr_type in instance.swagger_types.items():
            property = instance.attribute_map[attr]
            if property in data:
                value = data[property]
                setattr(instance, attr, self.__deserialize(value, attr_type))

        return instance

    @staticmethod
    def get_preferred_retry_strategy(operation_retry_strategy, client_retry_strategy):
        """
        Gets the preferred Retry Strategy for the client
        :param operation_retry_strategy: (optional) Operation level Retry Strategy
        :param client_retry_strategy: (optional) Client level Retry Strategy
        :return: Preferred Retry Strategy.
        """
        retry_strategy = None
        if operation_retry_strategy:
            retry_strategy = operation_retry_strategy
        elif client_retry_strategy:
            retry_strategy = client_retry_strategy
        elif retry.GLOBAL_RETRY_STRATEGY:
            retry_strategy = retry.GLOBAL_RETRY_STRATEGY
        return retry_strategy

    def should_allow_control_chars(self, allow_control_chars):
        request_configuration = allow_control_chars
        client_configuration = self._allow_control_chars
        global_configuration = BaseClient.ALLOW_CONTROL_CHARACTERS

        # Check at the request level
        if request_configuration is not None:
            return request_configuration

        # Check at the client level
        if client_configuration is not None:
            return client_configuration

        # Check at the global level
        if global_configuration is True:
            return True

        return False

    def should_allow_template_per_realm(self):
        """
        Returns a boolean of whether or not we should use realm specific endpoint templates

        The highest precedence goes in decending order. The order: Client / Environment / Default (False)
        """
        client_configuration = self.client_level_realm_specific_endpoint_template_enabled
        env_configuration = os.environ.get(OCI_REALM_SPECIFIC_SERVICE_ENDPOINT_TEMPLATE_ENABLED)  # comes back as a string.

        # Check at the client level
        if client_configuration is not None:
            return client_configuration

        # Check at the environment level
        if env_configuration is not None:
            return env_configuration.lower() == 'true'

        # By default we should not allow this feature.
        return False
