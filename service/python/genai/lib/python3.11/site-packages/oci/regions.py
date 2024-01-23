# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import absolute_import
import os
import json
import logging
from enum import Enum

from . import regions_definitions
from . import service_endpoints
from oci.exceptions import InvalidAlloyConfig
from oci._vendor import six
from oci._vendor import requests
from oci._vendor.requests.exceptions import HTTPError, ConnectionError, RetryError
from oci._vendor.requests.adapters import HTTPAdapter
from oci._vendor.urllib3.util.retry import Retry

REGIONS_SHORT_NAMES = regions_definitions.REGIONS_SHORT_NAMES
REGION_REALMS = regions_definitions.REGION_REALMS
REALMS = regions_definitions.REALMS
REGIONS = regions_definitions.REGIONS

SERVICE_ENDPOINTS = service_endpoints.SERVICE_ENDPOINTS
SERVICE_ENDPOINTS['auth'] = 'https://auth.{domain}'

DOMAIN_FORMAT = "{region}.{secondLevelDomain}"

OCI_REGION_METADATA_ENV_VAR_NAME = "OCI_REGION_METADATA"

REALM_KEY_PROPERTY_NAME = "realmKey"
REALM_DOMAIN_COMPONENT_PROPERTY_NAME = "realmDomainComponent"
REGION_KEY_PROPERTY_NAME = "regionKey"
REGION_IDENTIFIER_PROPERTY_NAME = "regionIdentifier"

# Region Metadata schema
REGION_METADATA_KEYS = (REALM_KEY_PROPERTY_NAME,
                        REALM_DOMAIN_COMPONENT_PROPERTY_NAME,
                        REGION_KEY_PROPERTY_NAME,
                        REGION_IDENTIFIER_PROPERTY_NAME)

# Constants for getting region info from IMDS
METADATA_URL_BASE = 'http://169.254.169.254/opc/v2'
GET_REGION_URL = '{}/instance/regionInfo'.format(METADATA_URL_BASE)
METADATA_AUTH_HEADERS = {'Authorization': 'Bearer Oracle'}

# Constants for regions config file
REGIONS_CONFIG_FILE_PATH = os.path.join('~', '.oci', 'regions-config.json')

# Enumerate region information sources outside of lookups
ExternalSources = Enum('ExternalSources', ['REGIONS_CFG_FILE', 'ENV_VAR', 'IMDS', 'SECOND_LEVEL_DOMAIN_FALLBACK'])

# Constant env name for second level domain fallback.
DEFAULT_REALM_ENV_VARNAME = "OCI_DEFAULT_REALM"

# Variable for second_level_domain_fallback, initially empty string, but will be set to fallback if env.DEFAULT_REALM_ENV_VARNAME exists
second_level_domain_fallback = ""

# Dict to track if we have read the ExternalSources
# Reading from IMDS is opt-in and can be enabled by calling enable_instance_metadata_service()
_has_been_read_external_sources = {
    ExternalSources.REGIONS_CFG_FILE: False,
    ExternalSources.ENV_VAR: False,
    ExternalSources.IMDS: True,
    ExternalSources.SECOND_LEVEL_DOMAIN_FALLBACK: False
}

# Alloy config
_IS_ALLOY_MODE = False
OCI_ALLOY_REGION_COEXIST_ENV_VAR_NAME = "OCI_ALLOY_REGION_COEXIST"
_IS_ALLOY_REGION_COEXIST = False

ALLOY_PROVIDER_NAME = None

logger = logging.getLogger(__name__)


def is_region(region_name):
    region = region_name.lower()

    if region in REGIONS_SHORT_NAMES:
        return False
    if region not in REGIONS:
        return _check_and_add_region_metadata(region)
    return True


def is_region_short_name(region):
    region = region.lower()
    if region in REGIONS_SHORT_NAMES:
        return True

    if region in REGIONS:
        return False

    if _check_and_add_region_metadata(region):
        # Above call will return true if the requested region is now known, after considering additional sources
        # Check is needed if region short code was passed
        if region in REGIONS_SHORT_NAMES:
            return True

    return False


def get_region_from_short_name(region):
    region = region.lower()
    if not is_region_short_name(region):
        logger.debug("Could not find region information in lookups and any other sources")
        # Return the input string to allow fallback to OC1
        return region
    # Return region from lookup
    return REGIONS_SHORT_NAMES[region]


def get_realm_from_region(region):
    region = region.lower()
    # If short name is passed, get the long name
    # get_region_from_short_name also adds metadata from other sources
    region = get_region_from_short_name(region)
    if not is_region(region):
        logger.debug("Cannot find region information in lookups and other sources, defaulting to OC1 realm")
        return "oc1"
    else:
        return REGION_REALMS[region]


def endpoint_for(service, region=None, endpoint=None, service_endpoint_template=None, endpoint_service_name=None):
    """Returns the base URl for a service, either in the given region or at the specified endpoint.

    If endpoint and region are provided, endpoint is used.

    If the region information is not available in the existing maps, following sources are checked in order:
    1. Regions Configuration File at ~/.oci/regions-config.json
    2. Region Metadata Environment variable
    3. Instance Metadata Service

    Lookup from Instance Metadata Service is disabled by default. To enable, call enable_instance_metadata_service()

    The region metadata schema is:
    {
        "realmKey" : string,
        "realmDomainComponent" : string,
        "regionKey" : string,
        "regionIdentifier" : string
    }

    For example,  for the Sydney OC1 region, the schema would be filled out as follows:
    {
        "realmKey" : "OC1",
        "realmDomainComponent" : "oraclecloud.com",
        "regionKey" : "SYD",
        "regionIdentifier" : "ap-sydney-1"
     }

     If the region still cannot be resolved, we fall back to OC1 realm.

     If alloy mode is enabled, and OCI_ALLOY_REGION_COEXIST is not set, only the alloy regions are available. If you want
     to access OCI and alloy regions at the same time, please set OCI_ALLOY_REGION_COEXIST to True. Fallback to OC1 realm
     is not available when OCI_ALLOY_REGION_COEXIST is not set.

    """
    if not (endpoint or region):
        raise ValueError("Must supply either a region or an endpoint.")

    if endpoint:
        # endpoint takes priority
        return _format_endpoint(service, endpoint, service_endpoint_template, endpoint_service_name)

    region = region.lower()
    # If unable to find region information from existing maps, check the other sources and add
    if not (region in REGIONS or region in REGIONS_SHORT_NAMES):
        _check_and_add_region_metadata(region)
    return _endpoint_for(service, region, service_endpoint_template, endpoint_service_name)


def skip_instance_metadata_service():
    logger.debug("Disabling region metadata lookup from IMDS")
    _set_source_has_been_read(ExternalSources.IMDS)


def enable_instance_metadata_service():
    logger.debug("Enabling region metadata lookup from IMDS")
    _set_source_has_been_read(ExternalSources.IMDS, False)


def add_region_schema_for_alloy(region_metadata):
    """
    This method is called from the alloy_config.py file to register an alloy region.
    Args:
        region_metadata: dict
    """
    # If we are here, then alloy-config.json has already been processed by _process_region_metadata_from_alloy_config,
    # since that method is called while initialization. It also processes _IS_ALLOY_REGION_COEXIST and resets region info
    # and external sources accordingly, except for regions added through alloy-config.json file. Check coexists and
    # reset accordingly
    if not _IS_ALLOY_REGION_COEXIST:
        _reset_region_info()
    _add_alloy_regions(region_metadata)


def _set_source_has_been_read(source, value=True):
    _has_been_read_external_sources[source] = value


def _get_source_has_been_read(source):
    return _has_been_read_external_sources[source]


def _reset_region_info():
    logger.debug("Resetting regions information")
    global REGIONS_SHORT_NAMES, REGION_REALMS, REALMS, REGIONS
    REGIONS_SHORT_NAMES = {}
    REGION_REALMS = {}
    REALMS = {}
    REGIONS = []


def _add_region_information_to_override(region_metadata):
    if _check_valid_schema(region_metadata):
        region_metadata = {k: v.lower() for k, v in six.iteritems(region_metadata)}
        REGIONS_SHORT_NAMES[region_metadata[REGION_KEY_PROPERTY_NAME]] = region_metadata[
            REGION_IDENTIFIER_PROPERTY_NAME]
        REGION_REALMS[region_metadata[REGION_IDENTIFIER_PROPERTY_NAME]] = region_metadata[REALM_KEY_PROPERTY_NAME]
        REALMS[region_metadata[REALM_KEY_PROPERTY_NAME]] = region_metadata[REALM_DOMAIN_COMPONENT_PROPERTY_NAME]
        REGIONS.append(region_metadata[REGION_IDENTIFIER_PROPERTY_NAME])


def _add_alloy_regions(alloy_regions):
    logger.debug("Adding alloy regions from {}".format(alloy_regions))
    if isinstance(alloy_regions, list):
        for region_metadata in alloy_regions:
            _add_region_information_to_override(region_metadata)
    elif isinstance(alloy_regions, dict):
        _add_region_information_to_override(alloy_regions)
    else:
        raise TypeError("Invalid type for alloy regions. Please use a dictionary or a list of dictionaries")


def _process_region_metadata_from_alloy_config(alloy_regions_list):
    global _IS_ALLOY_REGION_COEXIST
    _IS_ALLOY_REGION_COEXIST = os.getenv(OCI_ALLOY_REGION_COEXIST_ENV_VAR_NAME)
    if _IS_ALLOY_REGION_COEXIST and _IS_ALLOY_REGION_COEXIST.lower() in ["true", "1"]:
        _IS_ALLOY_REGION_COEXIST = True
    else:
        _IS_ALLOY_REGION_COEXIST = False

    # If IS_ALLOY_REGION_COEXIST is false and alloy is true then set all sources except OCI_DEFAULT_REALM has been read,
    # reset regions data structures, add alloy regions
    if _IS_ALLOY_MODE and not _IS_ALLOY_REGION_COEXIST:
        _reset_region_info()
        for source in _has_been_read_external_sources:
            _set_source_has_been_read(source)
        _set_source_has_been_read(ExternalSources.SECOND_LEVEL_DOMAIN_FALLBACK, False)
        _add_alloy_regions(alloy_regions_list)

    # If coexist is true and alloy is true, add alloy regions and override existing regions with alloy config
    if _IS_ALLOY_MODE and _IS_ALLOY_REGION_COEXIST:
        _add_alloy_regions(alloy_regions_list)


def _check_and_add_region_metadata(region):
    if not _get_source_has_been_read(ExternalSources.SECOND_LEVEL_DOMAIN_FALLBACK):
        global second_level_domain_fallback
        second_level_domain_fallback = os.environ.get(DEFAULT_REALM_ENV_VARNAME)
        _set_source_has_been_read(ExternalSources.SECOND_LEVEL_DOMAIN_FALLBACK)

    # Follow the hierarchy of sources
    if _set_region_metadata_from_cfg_file(region):
        logger.debug("Added metadata information for {} region from regions config file".format(region))
        return True
    elif _set_region_metadata_from_env_var(region):
        logger.debug("Added metadata information for {} region from environment variable".format(region))
        return True
    elif _set_region_from_instance_metadata_service(region):
        logger.debug("Added metadata information for {} region from IMDS".format(region))
        return True
    elif '.' in region:
        logger.debug("Unknown regionId '{}', contains '.', will use it as domain (<service>.<domain>)".format(region))
        return False
    elif second_level_domain_fallback:
        logger.debug("Unknown regionId '{}', default realm is defined, will fallback to '{}'".format(region, second_level_domain_fallback))
        return False
    elif _IS_ALLOY_MODE and not _IS_ALLOY_REGION_COEXIST:
        logger.debug("You're using the {provider} Alloy configuration file, the region you're targeting is not declared"
                     " in this config file. Please check if this is the correct region you're targeting or contact the {provider} "
                     "cloud provider for help. If you want to target both OCI regions and {provider} regions, please set the "
                     "OCI_ALLOY_REGION_COEXIST env var to True.".format(provider=ALLOY_PROVIDER_NAME))

    else:
        logger.debug("Unknown regionId '{}', will assume it's in Realm OC1".format(region))
    return False


def _set_region_metadata_from_cfg_file(region):
    # Check if region information from regions cfg file has already been read
    if _get_source_has_been_read(ExternalSources.REGIONS_CFG_FILE):
        # Return False to allow fallback
        return False

    # Set source as read
    _set_source_has_been_read(ExternalSources.REGIONS_CFG_FILE)

    expanded_file_location = os.path.expanduser(REGIONS_CONFIG_FILE_PATH)
    if os.path.isfile(expanded_file_location):
        logger.debug("Regions configuration file found")
        try:
            with open(expanded_file_location, 'r') as regions_config_file:
                regions_metadata_raw = regions_config_file.read()
        except (OSError, IOError) as e:
            logger.debug("Reading regions configuration file failed because of error: {}".format(e))
            return False

        # Try importing JSONDecodeError for Python 2 and Python 3 compatibility
        try:
            from json.decoder import JSONDecodeError
        except ImportError:
            JSONDecodeError = ValueError
        try:
            regions_metadata_array = json.loads(regions_metadata_raw)
        except JSONDecodeError as e:
            # Unable to parse the json array
            logger.debug("Decoding JSON array from regions configuration file failed because of error: {}".format(e))
            return False

        added = False
        for region_metadata in regions_metadata_array:
            if _check_valid_schema(region_metadata):
                if _add_region_information_to_lookup(region_metadata, region):
                    added = True
        return added
    return False


def _set_region_metadata_from_env_var(region):
    # Check if region information from env var has already been read
    if _get_source_has_been_read(ExternalSources.ENV_VAR):
        # Return False to allow fallback
        return False

    # Set source as read
    _set_source_has_been_read(ExternalSources.ENV_VAR)

    if os.environ.get(OCI_REGION_METADATA_ENV_VAR_NAME):
        # Try importing JSONDecodeError for Python 2 and Python 3 compatibility
        try:
            from json.decoder import JSONDecodeError
        except ImportError:
            JSONDecodeError = ValueError
        try:
            region_metadata = json.loads(os.environ.get(OCI_REGION_METADATA_ENV_VAR_NAME))
        except JSONDecodeError as e:
            # Unable to parse the env variable
            logger.debug("Decoding JSON from environment variable failed because of error: {}".format(e))
            return False

        if _check_valid_schema(region_metadata):
            return _add_region_information_to_lookup(region_metadata, region)

    return False


def _set_region_from_instance_metadata_service(region):
    # Check if region information from IMDS has already been read
    if _get_source_has_been_read(ExternalSources.IMDS):
        # Return False to allow fallback
        return False

    # Set source as read
    _set_source_has_been_read(ExternalSources.IMDS)

    try:

        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            read=0,
            connect=3,
            status=3
        )
        s = requests.Session()
        s.mount(GET_REGION_URL, HTTPAdapter(max_retries=retry_strategy))
        response = s.get(GET_REGION_URL, timeout=(10, 60), headers=METADATA_AUTH_HEADERS)
        region_metadata_raw = response.text
        logger.debug("Region metadata blob from IMDS is: {}".format(region_metadata_raw))
    except (HTTPError, ConnectionError, RetryError) as e:
        logger.debug("Failed to call IMDS service because of error: {}".format(e))
        return False

    if response.status_code != 200:
        logger.debug("HTTP Get Failed: URL: {}, Status: {}, Message: {}".format(GET_REGION_URL, response.status_code, response.text))
        return False

    try:
        from json.decoder import JSONDecodeError
    except ImportError:
        JSONDecodeError = ValueError
    try:
        region_metadata = json.loads(region_metadata_raw)
    except JSONDecodeError as e:
        # Unable to parse the raw response
        logger.debug("Decoding JSON from IMDS service because of error: {}".format(e))
        return False

    if _check_valid_schema(region_metadata):
        return _add_region_information_to_lookup(region_metadata, region)

    return False


def _check_valid_schema(region_metadata):
    for key in REGION_METADATA_KEYS:
        if key not in region_metadata:
            logger.debug("Key {} not found in region metadata".format(key))
            return False
        if region_metadata[key] == "":
            logger.debug("Value for key {} in region metadata is empty".format(key))
            return False
    return True


def _add_region_information_to_lookup(region_metadata, region=None):
    # Check if the region metadata has information about the requested region
    # Add the region information from region_metadata to the existing lookups
    region_metadata = {k: v.lower() for k, v in six.iteritems(region_metadata)}
    if region_metadata[REGION_KEY_PROPERTY_NAME] not in REGIONS_SHORT_NAMES:
        REGIONS_SHORT_NAMES[region_metadata[REGION_KEY_PROPERTY_NAME]] = region_metadata[REGION_IDENTIFIER_PROPERTY_NAME]

    if region_metadata[REGION_IDENTIFIER_PROPERTY_NAME] not in REGION_REALMS:
        REGION_REALMS[region_metadata[REGION_IDENTIFIER_PROPERTY_NAME]] = region_metadata[REALM_KEY_PROPERTY_NAME]

    if region_metadata[REALM_KEY_PROPERTY_NAME] not in REALMS:
        REALMS[region_metadata[REALM_KEY_PROPERTY_NAME]] = region_metadata[REALM_DOMAIN_COMPONENT_PROPERTY_NAME]

    if region_metadata[REGION_IDENTIFIER_PROPERTY_NAME] not in REGIONS:
        REGIONS.append(region_metadata[REGION_IDENTIFIER_PROPERTY_NAME])

    # Return True if the requested region is now known
    if region == region_metadata[REGION_IDENTIFIER_PROPERTY_NAME] or region == region_metadata[REGION_KEY_PROPERTY_NAME]:
        return True

    return False


def _endpoint_for(service, region=None, service_endpoint_template=None, endpoint_service_name=None):
    # Convert short code to region identifier
    if region in REGIONS_SHORT_NAMES:
        region = REGIONS_SHORT_NAMES[region]
    # for backwards compatibility, if region already has a '.'
    # then consider it the full domain and do not append '.oraclecloud.com'
    if '.' in region:
        if endpoint_service_name:
            endpoint = 'https://{}.{}'.format(endpoint_service_name, region)
            logger.debug("Construction endpoint from endpoint service name {} and region {} with '.' as domain. Endpoint: {}".format(endpoint_service_name, region, endpoint))
            return endpoint
        endpoint = _format_endpoint(service, region, service_endpoint_template, endpoint_service_name)
        return endpoint
    else:
        # get endpoint from template
        return _endpoint(service, region, service_endpoint_template)


def _endpoint(service, region, service_endpoint_template=None):
    if service_endpoint_template:
        endpoint = service_endpoint_template

        if region:
            endpoint = endpoint.replace("{region}", region)
        return endpoint.replace("{secondLevelDomain}", _second_level_domain(region))
    else:
        return _format_endpoint(service, DOMAIN_FORMAT.format(region=region, secondLevelDomain=_second_level_domain(region)))


def _second_level_domain(region):
    if not _get_source_has_been_read(ExternalSources.SECOND_LEVEL_DOMAIN_FALLBACK):
        global second_level_domain_fallback
        second_level_domain_fallback = os.environ.get(DEFAULT_REALM_ENV_VARNAME)
        _set_source_has_been_read(ExternalSources.SECOND_LEVEL_DOMAIN_FALLBACK)

    if region in REGION_REALMS.keys():
        realm = REGION_REALMS[region]
    elif second_level_domain_fallback:
        # if second_level_domain_fallback exists, default to using "unknown" realm
        # second_level_domain_fallback as the second level domain
        REALMS["unknown"] = second_level_domain_fallback
        realm = "unknown"
    else:
        # default realm to OC1 when available
        if 'oc1' not in REALMS:
            raise InvalidAlloyConfig("Fallback to default OCI region is blocked. This is likely happening if you are "
                                     "trying to access an alloy region not defined in the alloy region sources, and "
                                     "the env var OCI_ALLOY_REGION_COEXIST is not set to True.")
        realm = 'oc1'
    return REALMS[realm]


def _format_endpoint(service, domain, service_endpoint_template=None, endpoint_service_name=None):
    url_format = None

    if service.lower() not in SERVICE_ENDPOINTS:
        if service_endpoint_template is None:
            if endpoint_service_name:
                # No service_endpoint_template, but the spec specified the "service" portion of the endpoint in the spec
                url_format = "https://" + endpoint_service_name + ".{domain}"
            else:
                raise ValueError("Unknown service {!r}".format(service))
        else:
            # If there is no entry in SERVICE_ENDPOINTS and there is
            # a service_enpoint_template attempt to convert from new service template
            # to old template.
            # From "https://service.{region}.{subdomain}" to "https://service.{domain}"
            pos = service_endpoint_template.find("{region}")
            if pos != -1:
                url_format = service_endpoint_template[:pos] + "{domain}"
    else:
        url_format = SERVICE_ENDPOINTS[service.lower()]

    if url_format is None:
        raise ValueError("Unable to format endpoint for service, {} , and service_endpoint_template, {}".format(service, service_endpoint_template))

    endpoint = url_format.format(domain=domain)

    return endpoint
