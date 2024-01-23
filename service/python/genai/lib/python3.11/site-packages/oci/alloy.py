# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import absolute_import
import re
import os
import logging
import json

import oci.regions
import oci.regions_definitions
from oci.exceptions import InvalidAlloyConfig


OCI_ALLOY_FILE_PATH_ENV_VAR_NAME = "OCI_ALLOY_CONFIG_FILE_PATH"
ALLOY_CONFIG_FILE_PATH = os.path.join('~', '.oci', 'alloy-config.json')

ALLOY_CONFIG_SERVICE_KEY_NAME = "services"
ALLOY_CONFIG_REGIONS_KEY_NAME = "regions"
ALLOY_CONFIG_PROVIDER_KEY_NAME = "alloyProvider"
ALLOY_CONFIG_REGION_COEXIST_KEY_NAME = "ociRegionCoexist"
ALLOY_CONFIG_SCHEMA_REQUIRED_KEYS = (ALLOY_CONFIG_SERVICE_KEY_NAME,
                                     ALLOY_CONFIG_REGIONS_KEY_NAME)
ALLOY_CONFIG_SCHEMA_OPTIONAL_KEYS = (ALLOY_CONFIG_REGION_COEXIST_KEY_NAME,
                                     ALLOY_CONFIG_PROVIDER_KEY_NAME)
logger = logging.getLogger(__name__)


def _enable_alloy_mode():
    if not oci.regions._IS_ALLOY_MODE:
        logger.debug("Alloy mode detected")
        oci.regions._IS_ALLOY_MODE = True


# Class to define the behavior of the set containing services enabled by the alloy provider
class OciSdkEnabledServicesSet(object):

    def __init__(self):
        self._enabled_services_set = set()
        self._cleared_set_for_user_override = False

    def _clean_up_service_name_string(self, service_name):
        # By default, the OCI Python SDK uses underscores in the module name for services, however, the service names in
        # OCI_SDK_ENABLED_SERVICES_SET are expected without underscores, in lower case
        return re.sub('[^a-z]+', '', service_name.lower())

    def add(self, service_name, override_by_user=True):
        if not self._cleared_set_for_user_override and override_by_user:
            logger.warning("WARNING: Clearing OCI_SDK_ENABLED_SERVICES_SET to allow user override through code")
            self.clear()
            # Set _cleared_set_for_user_override to true, to clear the set only once
            self._cleared_set_for_user_override = True
        clean_service_name_string = self._clean_up_service_name_string(service_name)
        self._enabled_services_set.add(clean_service_name_string)

    def isempty(self):
        return len(self._enabled_services_set) == 0

    def clear(self):
        self._enabled_services_set.clear()

    def is_service_enabled(self, service_name):
        # If OCI_SDK_ENABLED_SERVICES_SET is empty, all the services are enabled
        if self.isempty():
            return True
        clean_service_name_string = self._clean_up_service_name_string(service_name)
        return clean_service_name_string in self._enabled_services_set


OCI_SDK_ENABLED_SERVICES_SET = OciSdkEnabledServicesSet()


def _validate_alloy_config_schema(alloy_config_json_object):
    for key in ALLOY_CONFIG_SCHEMA_REQUIRED_KEYS:
        if key not in alloy_config_json_object:
            logger.debug("Key {} not found in alloy config".format(key))
            raise InvalidAlloyConfig("Alloy config is invalid. Missing required key {}".format(key))
    for key in ALLOY_CONFIG_SCHEMA_OPTIONAL_KEYS:
        if key in alloy_config_json_object and key is ALLOY_CONFIG_REGION_COEXIST_KEY_NAME:
            if not isinstance(alloy_config_json_object[key], (bool, str)):
                raise InvalidAlloyConfig("{} must be either bool or str".format(ALLOY_CONFIG_REGION_COEXIST_KEY_NAME))
            if isinstance(alloy_config_json_object[key], str) and alloy_config_json_object[key].lower() not in ("true", "false"):
                raise InvalidAlloyConfig("Allowed values for {} are either true or false".format(ALLOY_CONFIG_REGION_COEXIST_KEY_NAME))
    return True


def _add_services_from_alloy_config(alloy_config_services_list):
    if alloy_config_services_list:
        for service in alloy_config_services_list:
            OCI_SDK_ENABLED_SERVICES_SET.add(service, override_by_user=False)


def _set_alloy_config_from_file():
    """
    Looks for alloy-config.json and parses enabled services and regions information from it
    Default location is ~/.oci/alloy-config.json
    Default location can be overridden by setting environment variable OCI_ALLOY_CONFIG_FILE_PATH
    """
    if os.getenv(OCI_ALLOY_FILE_PATH_ENV_VAR_NAME):
        config_file_location = os.getenv(OCI_ALLOY_FILE_PATH_ENV_VAR_NAME)
        logger.debug("Overriding default path for alloy-config.json to {}".format(OCI_ALLOY_FILE_PATH_ENV_VAR_NAME))
    else:
        config_file_location = ALLOY_CONFIG_FILE_PATH
    expanded_file_location = os.path.expanduser(config_file_location)
    if os.path.isfile(expanded_file_location):
        _enable_alloy_mode()
        logger.debug("Alloy configuration file found at location {}".format(expanded_file_location))
        try:
            with open(expanded_file_location, 'r') as alloy_config_file:
                alloy_config_raw_file_content = alloy_config_file.read()
        except (OSError, IOError) as e:
            logger.debug("Reading alloy configuration file failed because of error: {}".format(e))
            raise e
        try:
            alloy_config_json_object = json.loads(alloy_config_raw_file_content)
        except json.JSONDecodeError as e:
            # Unable to parse the json array
            logger.debug("Decoding JSON array from alloy configuration file failed because of error: {}".format(e))
            raise e

        if _validate_alloy_config_schema(alloy_config_json_object):
            # Extract enabled services and regions from alloy_config_json_object
            _add_services_from_alloy_config(alloy_config_json_object[ALLOY_CONFIG_SERVICE_KEY_NAME])
            oci.regions._IS_ALLOY_REGION_COEXIST = alloy_config_json_object.get(ALLOY_CONFIG_REGION_COEXIST_KEY_NAME,
                                                                                False)
            oci.regions._process_region_metadata_from_alloy_config(alloy_config_json_object[ALLOY_CONFIG_REGIONS_KEY_NAME])
            oci.regions.ALLOY_PROVIDER_NAME = alloy_config_json_object.get(ALLOY_CONFIG_PROVIDER_KEY_NAME, False)


def _configure_alloy_mode():
    """
    Determines if alloy specific inputs are provided and configures the SDK for alloy mode
    Alloy mode is enabled if alloy-config.json file is found
    """
    # Read all the sources to determine alloy mode
    _set_alloy_config_from_file()


_configure_alloy_mode()
