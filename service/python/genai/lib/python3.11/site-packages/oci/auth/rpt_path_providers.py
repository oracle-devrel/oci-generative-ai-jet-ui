# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import absolute_import
import abc
import os
import logging
import time

from oci._vendor import requests
import oci._vendor.jwt as jwt

from .signers.instance_principals_security_token_signer import InstancePrincipalsSecurityTokenSigner

OCI_RESOURCE_PRINCIPAL_RPT_PATH = "OCI_RESOURCE_PRINCIPAL_RPT_PATH"
OCI_RESOURCE_PRINCIPAL_RPT_ID = "OCI_RESOURCE_PRINCIPAL_RPT_ID"
OCI_RESOURCE_PRINCIPAL_RPT_PATH_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPT_PATH_FOR_LEAF_RESOURCE"
OCI_RESOURCE_PRINCIPAL_RPT_ID_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPT_ID_FOR_LEAF_RESOURCE"
IMDS_PATH_TEMPLATE = "/20180711/resourcePrincipalToken/{id}"
METADATA_AUTH_HEADERS = {'Authorization': 'Bearer Oracle'}
OCI_KUBERNETES_SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

logger = logging.getLogger(__name__)


class RptPathProviderInterface(object):
    """An informal interface which returns the complete RPT path"""
    def get_path(self):
        pass


class StringRptPathProvider(RptPathProviderInterface):
    def __init__(self, path):
        self.path = path
        logger.debug("Found String RPT Path Provider with path {}".format(path))

    def get_path(self):
        return self.path


class AbstractRptPathProvider(RptPathProviderInterface):
    """This abstract path provider has a string template with placeholders like {id},
    and provides a way to get a mapping of substitutions to fill in"""
    __metaclass__ = abc.ABCMeta

    def __init__(self, path_template):
        self.path_template = path_template

    def get_path(self):
        replacements = self.get_replacements()
        path = self.path_template.format(**replacements)
        logger.debug("Using path {}".format(path))
        return path

    @abc.abstractmethod
    def get_replacements(self):
        pass


class ImdsRptPathProvider(AbstractRptPathProvider):
    def __init__(self):
        super(ImdsRptPathProvider, self).__init__(self.get_path_template())
        self.replacements = self.build_replacements()

    def get_replacements(self):
        return self.replacements

    def get_path_template(self):
        return IMDS_PATH_TEMPLATE

    def build_replacements(self):
        # Get instance ID from IMDS
        return {'id': get_instance_id_from_imds()}


class EnvRptPathProvider(AbstractRptPathProvider):
    def __init__(self, **kwargs):
        if kwargs.get("child_resource", False):
            self.child_resource = True
        else:
            self.child_resource = False
        super(EnvRptPathProvider, self).__init__(self.get_path_template())
        self.replacements = self.build_replacements()

    def get_replacements(self):
        return self.replacements

    def get_path_template(self):
        if self.child_resource:
            return os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_PATH_FOR_LEAF_RESOURCE)
        return os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_PATH)

    def build_replacements(self):
        if self.child_resource:
            rpt_id = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_ID_FOR_LEAF_RESOURCE)
        else:
            rpt_id = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_ID)
        if rpt_id:
            return {'id': rpt_id}
        return None


class DefaultRptPathProvider(AbstractRptPathProvider):
    """
    This path provider makes sure the behavior happens with the correct fallback.

    For the path,
    Use the contents of the OCI_RESOURCE_PRINCIPAL_RPT_PATH environment variable, if set.
    Otherwise, use the current path: "/20180711/resourcePrincipalToken/{id}"

    For the resource id,
    Use the contents of the OCI_RESOURCE_PRINCIPAL_RPT_ID environment variable, if set.
    Otherwise, use IMDS to get the instance id

    This path provider is used when the caller doesn't provide a specific path provider to the resource principals signer
    """

    def __init__(self, **kwargs):
        logger.debug("A path provider was not specified, using DefaultRptPathProvider")
        self.env_rpt_path_provider = EnvRptPathProvider(**kwargs)
        self.imds_rpt_path_provider = ImdsRptPathProvider()
        super(DefaultRptPathProvider, self).__init__(self.get_path_template())
        self.replacements = self.build_replacements()

    def get_path_template(self):
        path_template = self.env_rpt_path_provider.get_path_template()
        if not path_template:
            logger.debug("Unable to get path template from {} env variable, using IMDS template".format(OCI_RESOURCE_PRINCIPAL_RPT_PATH))
            path_template = self.imds_rpt_path_provider.get_path_template()
        logger.debug("The path template is {}".format(path_template))
        return path_template

    def build_replacements(self):
        replacements = self.env_rpt_path_provider.build_replacements()
        if not replacements:
            logger.debug("Unable to get replacements from {} env variable, getting replacements from IMDS".format(OCI_RESOURCE_PRINCIPAL_RPT_ID))
            replacements = self.imds_rpt_path_provider.build_replacements()
        logger.debug("The replacement dict is {}".format(replacements))
        return replacements

    def get_replacements(self):
        return self.replacements


class DefaultServiceAccountTokenProvider(object):
    def __init__(self):
        self.token_path = OCI_KUBERNETES_SERVICE_ACCOUNT_TOKEN_PATH

    def override_sa_token_path(self, new_token_path):
        self.token_path = new_token_path

    def get_sa_token(self):
        token_path = os.path.expanduser(self.token_path)
        with open(token_path, mode="r", encoding="utf-8") as f:
            sa_token = f.read().strip()
        is_sa_token_valid = is_valid_sa_token(sa_token)
        if is_sa_token_valid is False:
            raise RuntimeError("Service account token at {} has expired".format(self.token_path))
        return sa_token


class SuppliedServiceAccountTokenProvider(object):
    def __init__(self, token_string):
        self.token_string = token_string

    def get_sa_token(self):
        is_sa_token_valid = is_valid_sa_token(self.token_string)
        if is_sa_token_valid is False:
            raise RuntimeError("The supplied service account token has expired.")
        return self.token_string


def get_instance_id_from_imds():
    # Get the instance id from the metadata service
    # TODO add error checks to ensure instance_id was retrieved.
    endpoint = '{}/instance/id'.format(InstancePrincipalsSecurityTokenSigner.METADATA_URL_BASE)
    # Set the connect time out to 10 seconds and the read time out to 60 seconds.
    timeout = (10, 60)
    response = requests.get(endpoint, timeout=timeout, headers=METADATA_AUTH_HEADERS)
    return response.text.strip().lower()


def is_valid_sa_token(token):
    decoded_jwt = jwt.decode(jwt=token, verify=False)
    time_now = int(time.time())
    if decoded_jwt.get('exp') is None:
        raise RuntimeError("Service account token does not have an 'exp' field.")
    return time_now < decoded_jwt['exp']
