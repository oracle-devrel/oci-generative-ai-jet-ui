# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

"""
Helpers for loading and validating service configuration.

You can configure services by passing a config dict directly, or by loading
one from a configuration file.

The following keys are required::

    fingerprint
    key_file
    region
    tenancy
    user

Additionally, the following keys are optional::

    additional_user_agent (default "")
    log_requests (default False)
    pass_phrase (required if your key_file has a passphrase)

"""

from __future__ import absolute_import
import configparser
import os
import re
import logging
from oci._vendor import six

from .exceptions import ConfigFileNotFound, ProfileNotFound, InvalidConfig, InvalidKeyFilePath
from .auth import signers
from .util import AUTHENTICATION_TYPE_FIELD_NAME, get_authentication_type_from_config, DELEGATION_TOKEN_FILE_FIELD_NAME, DELEGATION_TOKEN_WITH_INSTANCE_PRINCIPAL_AUTHENTICATION_TYPE

__all__ = ["DEFAULT_CONFIG", "from_file", "validate_config"]

DEFAULT_CONFIG = {
    "log_requests": False,
    "additional_user_agent": "",
    "pass_phrase": None
}
DEFAULT_LOCATION = os.path.join('~', '.oci', 'config')
FALLBACK_DEFAULT_LOCATION = os.path.join('~', '.oraclebmc', 'config')
DEFAULT_PROFILE = "DEFAULT"
PATTERNS = {
    # Tenancy and user have the same shape
    "tenancy": re.compile(r"^([0-9a-zA-Z-_]+[.:])([0-9a-zA-Z-_]*[.:]){3,}([0-9a-zA-Z-_]+)$"),
    "user": re.compile(r"^([0-9a-zA-Z-_]+[.:])([0-9a-zA-Z-_]*[.:]){3,}([0-9a-zA-Z-_]+)$"),
    "fingerprint": re.compile(r"^([0-9a-f]{2}:){15}[0-9a-f]{2}$")
}
REQUIRED = {
    "user",
    "tenancy",
    "fingerprint",
    "key_file",
    "region"
}
REQUIRED_FALLBACKS = {
    "key_file": "key_content"
}
CONFIG_FILE_BLACKLISTED_KEYS = {
    "key_content"
}

CONFIG_FILE_PATH_ENV_VAR_NAME = "OCI_CONFIG_FILE"
REGION_ENV_VAR_NAME = "OCI_REGION"
REGION_KEY_NAME = "region"
CONFIG_FILE_DEBUG_INFORMATION_LOG = "For more info about config file and how to get required information, see https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm"

logger = logging.getLogger(__name__)


def _validate_delegation_token_with_instance_principal(config):
    # At this point we know we have the required fields for this authentication type, so we won't check that again
    delegation_token_file_path = config.get(DELEGATION_TOKEN_FILE_FIELD_NAME)
    if delegation_token_file_path is None:
        raise InvalidConfig('ERROR: Please specify the location of the delegation_token_file in the config.')

    expanded_delegation_token_file_path = os.path.expanduser(delegation_token_file_path)

    if not os.path.isfile(expanded_delegation_token_file_path):
        raise InvalidConfig("Delegation token file not found at {}".format(expanded_delegation_token_file_path))


# Map the validator function for each type
# This can easily be extended to support other auth types
AUTH_TYPE_TO_VALIDATION_FUNCTION_MAP = {
    DELEGATION_TOKEN_WITH_INSTANCE_PRINCIPAL_AUTHENTICATION_TYPE: _validate_delegation_token_with_instance_principal
}


def from_file(file_location=DEFAULT_LOCATION, profile_name=DEFAULT_PROFILE):
    """Create a config dict from a file.

    :param file_location: Path to the config file.  Defaults to ~/.oci/config and with a fallback
                            to environment variable OCI_CONFIG_FILE, then ~/.oraclebmc/config.
    :param profile_name: The profile to load from the config file.  Defaults to "DEFAULT"
    :return: A config dict that can be used to create clients.
    """
    expanded_file_location = _get_config_path_with_fallback(file_location)

    parser = configparser.ConfigParser(interpolation=None)
    if not parser.read(expanded_file_location):
        raise ConfigFileNotFound("Could not find config file at {}, please follow the instructions in the link to setup the config file https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm".format(expanded_file_location))

    if profile_name not in parser:
        raise ProfileNotFound("Profile '{}' not found in config file {} ".format(profile_name, expanded_file_location) + CONFIG_FILE_DEBUG_INFORMATION_LOG)

    config = dict(DEFAULT_CONFIG)
    config.update(parser[profile_name])
    config["log_requests"] = _as_bool(config["log_requests"])

    for key in CONFIG_FILE_BLACKLISTED_KEYS:
        if key in config:
            raise ValueError("'{}' cannot be specified in a config file for security reasons. To use this key you must add it to the config programmatically. ".format(key) + CONFIG_FILE_DEBUG_INFORMATION_LOG)

    invalid_key_file_path_checker(config, expanded_file_location, profile_name)

    return config


def validate_config(config, **kwargs):
    if 'signer' in kwargs:
        # InstancePrincipalsSecurityTokenSigner and  SecurityTokenSigner are
        # self-sufficient and do not need to read the normally-required keys
        # in the config
        if isinstance(kwargs['signer'], signers.InstancePrincipalsSecurityTokenSigner) or isinstance(kwargs['signer'], signers.SecurityTokenSigner) or isinstance(kwargs['signer'], signers.KeyPairSigner):
            return

    if AUTHENTICATION_TYPE_FIELD_NAME in config:
        auth_type = get_authentication_type_from_config(config)
        validator_function = AUTH_TYPE_TO_VALIDATION_FUNCTION_MAP.get(auth_type)
        validator_function(config)
        return

    """Raises ValueError if required fields are missing or malformed."""
    errors = {}
    for required_key in REQUIRED:
        fallback_key = REQUIRED_FALLBACKS.get(required_key)
        if (required_key not in config or config[required_key] is None) and (fallback_key not in config or config[fallback_key] is None):
            # If region is not provided, check the env variable
            if required_key == REGION_KEY_NAME:
                logger.debug("Region not found in config, checking environment variable {}".format(REGION_ENV_VAR_NAME))
                region_from_env_var = os.environ.get(REGION_ENV_VAR_NAME)
                if region_from_env_var:
                    # If present, inject the region in config
                    logger.debug("Setting region from environment variable {}".format(REGION_ENV_VAR_NAME))
                    config[REGION_KEY_NAME] = region_from_env_var
                else:
                    errors[required_key] = "missing"
            else:
                errors[required_key] = "missing"

    for key, pattern in six.iteritems(PATTERNS):
        if key in errors:
            # key is missing, can't possibly match pattern
            continue
        if not pattern.match(config[key]):
            errors[key] = "malformed"
    if errors:
        raise InvalidConfig(errors)


def get_config_value_or_default(config, key):
    return config.get(key, DEFAULT_CONFIG.get(key))


def _as_bool(x):
    if x in [True, False]:
        return x
    if x.lower() in ["1", "yes", "true", "on"]:
        return True
    elif x.lower() in ["0", "no", "false", "off"]:
        return False
    else:
        raise ValueError("{!r} is not a valid alias for True/False".format(x))


def _raise_on_errors(errors):
    # report all errors at once
    if len(errors) == 1:
        raise ValueError("Error in config: {}".format(errors[0]))
    elif errors:
        raise ValueError("Found the following config errors: {!r}".format(errors))


def _get_config_path_with_fallback(file_location):
    expanded_file_location = os.path.expanduser(file_location)
    expanded_fallback_default_file_location = os.path.expanduser(FALLBACK_DEFAULT_LOCATION)

    if (file_location != DEFAULT_LOCATION) or (file_location == DEFAULT_LOCATION and os.path.isfile(expanded_file_location)):
        logger.debug("Config file found at {}".format(file_location))
        return expanded_file_location

    # If file location is not specified and the default file (~/.oci/config) does not exist
    # then try getting config file path from env var
    elif os.environ.get(CONFIG_FILE_PATH_ENV_VAR_NAME):
        logger.debug(
            "No file location specified and default file does not exist. Getting path info from the environment variable {}".format(
                CONFIG_FILE_PATH_ENV_VAR_NAME))
        expanded_file_location = os.path.expanduser(os.environ.get(CONFIG_FILE_PATH_ENV_VAR_NAME))
        return expanded_file_location

    # If we cannot determine the path from any other source and the fallback path (~/.oraclebmc/config) exists,
    # use that path
    elif os.path.isfile(expanded_fallback_default_file_location):
        expanded_file_location = expanded_fallback_default_file_location
        return expanded_file_location

    logger.debug("Config file found at {}".format(expanded_file_location))
    return expanded_file_location


def invalid_key_file_path_checker(config, expanded_file_location, profile_name):
    if 'key_file' in config:
        key_file_path = os.path.expanduser(config.get('key_file'))
        if not os.path.isfile(key_file_path):
            line_number = get_linenum_from_file(config.get('key_file'), expanded_file_location, profile_name)
            line_message = " at line {}".format(line_number) if line_number else ""
            message = "Config file {} is invalid: the key_file's value \'{}\'{} must be a valid file path. ".format(expanded_file_location, key_file_path, line_message) + CONFIG_FILE_DEBUG_INFORMATION_LOG
            raise InvalidKeyFilePath(message)


def get_linenum_from_file(key, filename, profile):
    with open(filename, 'r') as f:
        profile_found = False
        profile_token = "[" + profile + "]"
        for line_number, line in enumerate(f):
            line = line.strip()
            if len(line) >= 1:
                if line[0] == "#":
                    continue
            if profile_token in line:
                profile_found = True
            if profile_found and key in line:
                return line_number + 1
    return None
