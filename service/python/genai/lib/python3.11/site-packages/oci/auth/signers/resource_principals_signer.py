# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import os
from .resource_principals_federation_signer import ResourcePrincipalsFederationSigner
from .resource_principals_delegation_token_signer import ResourcePrincipalsDelegationTokenSigner
from .ephemeral_resource_principals_signer import EphemeralResourcePrincipalSigner
from .ephemeral_resource_principals_delegation_token_signer import EphemeralResourcePrincipalsDelegationTokenSigner
from .ephemeral_resource_principals_v21_signer import EphemeralResourcePrincipalV21Signer
from .oke_workload_identity_resource_principal_signer import OkeWorkloadIdentityResourcePrincipalSigner
from ..rpt_path_providers import DefaultServiceAccountTokenProvider, SuppliedServiceAccountTokenProvider
from .nested_resource_principals_signer import NestedResourcePrincipals

OCI_RESOURCE_PRINCIPAL_VERSION = "OCI_RESOURCE_PRINCIPAL_VERSION"
OCI_RESOURCE_PRINCIPAL_RPST = "OCI_RESOURCE_PRINCIPAL_RPST"
OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM = "OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM"
OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE = "OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE"
OCI_RESOURCE_PRINCIPAL_REGION = "OCI_RESOURCE_PRINCIPAL_REGION"
OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT = "OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT"
OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT = "OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT"
OCI_RESOURCE_PRINCIPAL_RESOURCE_ID = "OCI_RESOURCE_PRINCIPAL_RESOURCE_ID"
OCI_RESOURCE_PRINCIPAL_TENANCY_ID = "OCI_RESOURCE_PRINCIPAL_TENANCY_ID"

# Resource Principal v3.0
OCI_RESOURCE_PRINCIPAL_VERSION_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_VERSION_FOR_LEAF_RESOURCE"
# For 1.1 LEAF-resource
OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT_FOR_LEAF_RESOURCE"
OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_LEAF_RESOURCE"
# For 2.2 LEAF-resource
OCI_RESOURCE_PRINCIPAL_RPST_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPST_FOR_LEAF_RESOURCE"
OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_FOR_LEAF_RESOURCE"
OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE_FOR_LEAF_RESOURCE"
OCI_RESOURCE_PRINCIPAL_REGION_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_REGION_FOR_LEAF_RESOURCE"
# For 2.1/2.1.1 LEAF-resource
OCI_RESOURCE_PRINCIPAL_RESOURCE_ID_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RESOURCE_ID_FOR_LEAF_RESOURCE"
OCI_RESOURCE_PRINCIPAL_TENANCY_ID_FOR_LEAF_RESOURCE = "OCI_RESOURCE_PRINCIPAL_TENANCY_ID_FOR_LEAF_RESOURCE"
# For Parent Resource
OCI_RESOURCE_PRINCIPAL_RPT_URL_FOR_PARENT_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPT_URL_FOR_PARENT_RESOURCE"
OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT_FOR_PARENT_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT_FOR_PARENT_RESOURCE"
OCI_RESOURCE_PRINCIPAL_RPT_PATH_FOR_PARENT_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPT_PATH_FOR_PARENT_RESOURCE"
OCI_RESOURCE_PRINCIPAL_RPT_ID_FOR_PARENT_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPT_ID_FOR_PARENT_RESOURCE"
OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_PARENT_RESOURCE = "OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_PARENT_RESOURCE"
MAX_NESTED_PARENT_DEPTH = 10

OCI_KUBERNETES_SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
DEFAULT_OCI_KUBERNETES_SERVICE_ACCOUNT_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
OCI_KUBERNETES_SERVICE_ACCOUNT_CERT_PATH = "OCI_KUBERNETES_SERVICE_ACCOUNT_CERT_PATH"
OCI_KUBERNETES_PROXYMUX_SERVICE_PORT = "12250"
KUBERNETES_SERVICE_HOST = "KUBERNETES_SERVICE_HOST"


def get_resource_principals_signer(resource_principal_token_path_provider=None):
    """
    A Resource Principals signer is token based signer.  The flavor of resource
    principals signer required is determined by the configured environment of
    the instance.

    returns: a resource principals signer
    """

    rp_version = os.environ.get(OCI_RESOURCE_PRINCIPAL_VERSION, "UNDEFINED")
    if rp_version == "3.0":
        """
            This signer utilizes a resource principals signer for the LEAF-resource, via the following environment variable:-
            - OCI_RESOURCE_PRINCIPAL_VERSION_FOR_LEAF_RESOURCE
                Based on the value of this variable we need different environment variable set.

            For 1.1 it needs:
            - OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT_FOR_LEAF_RESOURCE The endpoint for retrieving the Resource Principal Token for LEAF-resource
            - OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_LEAF_RESOURCE The endpoint for retrieving the Resource Principal Session Token for LEAF-resource

            For 2.1/2.1.1 it needs:
            - OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT_FOR_LEAF_RESOURCE: The endpoint for retrieving the Resource Principal Token
            - OCI_RESOURCE_PRINCIPAL_RESOURCE_ID_FOR_LEAF_RESOURCE: The RPv2.1/Rpv2.1.1 resource id
            - OCI_RESOURCE_PRINCIPAL_TENANCY_ID_FOR_LEAF_RESOURCE: The RPv2.1.1 tenancy id
            - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_FOR_LEAF_RESOURCE: The private key in PEM format
            - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE_FOR_LEAF_RESOURCE: The (optional) passphrase for the private key
            - OCI_RESOURCE_PRINCIPAL_REGION_FOR_LEAF_RESOURCE: the canonical region name

            For 2.2 it needs:
            - OCI_RESOURCE_PRINCIPAL_RPST_FOR_LEAF_RESOURCE: the Resource Principals Session Token
            - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_FOR_LEAF_RESOURCE: the private key in PEM format
            - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE_FOR_LEAF_RESOURCE: the (optional) passphrase for the private key
            - OCI_RESOURCE_PRINCIPAL_REGION_FOR_LEAF_RESOURCE: the canonical region name

            For the Parent resource the following environment variables need to be set:-
            - OCI_RESOURCE_PRINCIPAL_RPT_URL_FOR_PARENT_RESOURCE: The complete URL including API and resource if any to retrieve Resource Principal Token for the parent resource.
            - OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_PARENT_RESOURCE: The endpoint for retrieving the Resource Principal Session Token for parent resource
        """
        # Step 1: Get the Resource Principals signer for the sub resource.
        resource_principal_version_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_VERSION_FOR_LEAF_RESOURCE)
        if resource_principal_version_for_leaf_resource == "2.2":
            resource_session_token_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST_FOR_LEAF_RESOURCE)
            private_key_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_FOR_LEAF_RESOURCE)
            private_key_passphrase_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE_FOR_LEAF_RESOURCE)
            region_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_REGION_FOR_LEAF_RESOURCE)

            leaf_resource_rp_signer = EphemeralResourcePrincipalSigner(session_token=resource_session_token_for_leaf_resource,
                                                                       private_key=private_key_for_leaf_resource,
                                                                       private_key_passphrase=private_key_passphrase_for_leaf_resource,
                                                                       region=region_for_leaf_resource)
        elif resource_principal_version_for_leaf_resource in ["2.1", "2.1.1"]:
            resource_principal_token_endpoint_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT_FOR_LEAF_RESOURCE)
            resource_principal_session_token_endpoint_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_LEAF_RESOURCE)
            resource_id_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_RESOURCE_ID_FOR_LEAF_RESOURCE)
            tenancy_id_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_TENANCY_ID_FOR_LEAF_RESOURCE)
            private_key_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_FOR_LEAF_RESOURCE)
            private_key_passphrase_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE_FOR_LEAF_RESOURCE)
            region_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_REGION_FOR_LEAF_RESOURCE)

            leaf_resource_rp_signer = EphemeralResourcePrincipalV21Signer(resource_principal_token_endpoint=resource_principal_token_endpoint_for_leaf_resource,
                                                                          resource_principal_session_token_endpoint=resource_principal_session_token_endpoint_for_leaf_resource,
                                                                          resource_id=resource_id_for_leaf_resource,
                                                                          tenancy_id=tenancy_id_for_leaf_resource,
                                                                          private_key=private_key_for_leaf_resource,
                                                                          private_key_passphrase=private_key_passphrase_for_leaf_resource,
                                                                          rp_version=rp_version,
                                                                          region=region_for_leaf_resource)
        elif resource_principal_version_for_leaf_resource == "1.1":
            resource_principal_token_endpoint_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT_FOR_LEAF_RESOURCE)
            resource_principal_session_token_endpoint_for_leaf_resource = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_LEAF_RESOURCE)
            leaf_resource_rp_signer = ResourcePrincipalsFederationSigner(resource_principal_token_endpoint=resource_principal_token_endpoint_for_leaf_resource,
                                                                         resource_principal_session_token_endpoint=resource_principal_session_token_endpoint_for_leaf_resource,
                                                                         resource_principal_token_path_provider=resource_principal_token_path_provider,
                                                                         child_resource=True)
        else:
            raise EnvironmentError("Unsupported {}: {}".format(OCI_RESOURCE_PRINCIPAL_VERSION_FOR_LEAF_RESOURCE, resource_principal_version_for_leaf_resource))

        # Get values for First Parent Resource
        resource_principal_rpt_url = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_URL_FOR_PARENT_RESOURCE)
        resource_principal_session_token_endpoint = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT_FOR_PARENT_RESOURCE)
        nested_resource_principal = NestedResourcePrincipals(resource_principal_rpt_url=resource_principal_rpt_url,
                                                             resource_principal_session_token_endpoint=resource_principal_session_token_endpoint,
                                                             sub_resource_rp_signer=leaf_resource_rp_signer)

        # Terminal case when we reach terminal parent.
        if nested_resource_principal.nested_parent_rpt_url is None:
            return nested_resource_principal
        # If the recursion level for N level parent reaches MAX_NESTED_PARENT_DEPTH or the response HEADER contains
        # the same endpoint as the one it already has we will treat it as the terminal condition for recursion end
        elif nested_resource_principal.current_parent_depth >= MAX_NESTED_PARENT_DEPTH \
                or nested_resource_principal.nested_parent_rpt_url == nested_resource_principal.resource_principal_token_endpoint:
            raise AttributeError("The nested resource principals went over the max allowed recursion {}, or detected a cycle!".format(MAX_NESTED_PARENT_DEPTH))
        # We have another parent, so we create a new signer based off that
        else:
            return NestedResourcePrincipals(resource_principal_rpt_url=nested_resource_principal.nested_parent_rpt_url,
                                            resource_principal_session_token_endpoint=resource_principal_session_token_endpoint,
                                            sub_resource_rp_signer=nested_resource_principal,
                                            current_parent_depth=nested_resource_principal.current_parent_depth + 1)

    if rp_version == "2.2":
        """
        This signer takes its configuration from the following environment variables.
        - OCI_RESOURCE_PRINCIPAL_RPST: the Resource Principals Session Token
        - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM: the private key in PEM format
        - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE: the (optional) passphrase for the private key

            These three variables may be used in one of two modes. In the first mode, they contain the actual
            contents of the RPST, private key (in PEM format) and the passphrase. This mode is only useful for
            short-lived programs.

            In the second mode, if these variables contain absolute paths, then those paths are taken as the
            on-filesystem location of the values in question. The signer may attempt to reload these values from
            the filesystem on receiving a 401 response from an OCI service. This mode is used in cases where the
            program executes in an environment where an external provider may inject updated tokens into
            the filesystem.

        - OCI_RESOURCE_PRINCIPAL_REGION: the canonical region name

            This is utilized in locating the "local" endpoints of services.
        """
        session_token = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST)
        private_key = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM)
        private_key_passphrase = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE)
        region = os.environ.get(OCI_RESOURCE_PRINCIPAL_REGION)

        return EphemeralResourcePrincipalSigner(session_token=session_token,
                                                private_key=private_key,
                                                private_key_passphrase=private_key_passphrase,
                                                region=region)

    elif rp_version in ["2.1", "2.1.1"]:
        """
        This signer takes its configuration from the following environment variables.
            - OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT: The endpoint for retrieving the Resource Principal Token
            - OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT: The endpoint for retrieving the Resource Principal Session Token
            - OCI_RESOURCE_PRINCIPAL_RESOURCE_ID: The RPv2.1/Rpv2.1.1 resource id
            - OCI_RESOURCE_PRINCIPAL_TENANCY_ID: The RPv2.1.1 tenancy id
            - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM: The private key in PEM format
            - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE: The (optional) passphrase for the private key
            - OCI_RESOURCE_PRINCIPAL_REGION: The (optional) canonical region name
        """
        resource_principal_token_endpoint = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT)
        resource_principal_session_token_endpoint = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT)
        resource_id = os.environ.get(OCI_RESOURCE_PRINCIPAL_RESOURCE_ID)
        tenancy_id = os.environ.get(OCI_RESOURCE_PRINCIPAL_TENANCY_ID)
        private_key = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM)
        private_key_passphrase = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE)
        region = os.environ.get(OCI_RESOURCE_PRINCIPAL_REGION)

        return EphemeralResourcePrincipalV21Signer(resource_principal_token_endpoint=resource_principal_token_endpoint,
                                                   resource_principal_session_token_endpoint=resource_principal_session_token_endpoint,
                                                   resource_id=resource_id,
                                                   tenancy_id=tenancy_id,
                                                   private_key=private_key,
                                                   private_key_passphrase=private_key_passphrase,
                                                   rp_version=rp_version,
                                                   region=region)

    elif rp_version == "1.1":
        """
        This signer takes its configuration from the following environment variables
        - OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT
            The endpoint for retrieving the Resource Principal Token
        - OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT
            The endpoint for retrieving the Resource Principal Session Token
        """
        resource_principal_token_endpoint = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT)
        resource_principal_session_token_endpoint = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT)

        return ResourcePrincipalsFederationSigner(resource_principal_token_endpoint=resource_principal_token_endpoint,
                                                  resource_principal_session_token_endpoint=resource_principal_session_token_endpoint,
                                                  resource_principal_token_path_provider=resource_principal_token_path_provider)

    elif rp_version == "UNDEFINED":
        raise EnvironmentError("{} is not defined".format(OCI_RESOURCE_PRINCIPAL_VERSION))
    else:
        raise EnvironmentError("Unsupported {}: {}".format(OCI_RESOURCE_PRINCIPAL_VERSION, rp_version))


def get_resource_principal_delegation_token_signer(delegation_token, resource_principal_token_path_provider=None):
    """
        A Resource Principals delegation token signer is a delegation token based signer. The delegation token to be
        used is passed as a value to the signer instance and the flavor of resource principals signer required is
        determined by the configured environment of the instance.

        returns: a resource principals delegation token signer
        """
    rp_version = os.environ.get(OCI_RESOURCE_PRINCIPAL_VERSION, "UNDEFINED")
    if rp_version == "2.2":
        """
        This signer takes its configuration from the following environment variables.
        - OCI_RESOURCE_PRINCIPAL_RPST: the Resource Principals Session Token
        - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM: the private key in PEM format
        - OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE: the (optional) passphrase for the private key

            These three variables may be used in one of two modes. In the first mode, they contain the actual
            contents of the RPST, private key (in PEM format) and the passphrase. This mode is only useful for
            short-lived programs.

            In the second mode, if these variables contain absolute paths, then those paths are taken as the
            on-filesystem location of the values in question. The signer may attempt to reload these values from
            the filesystem on receiving a 401 response from an OCI service. This mode is used in cases where the
            program executes in an environment where an external provider may inject updated tokens into
            the filesystem.

        - OCI_RESOURCE_PRINCIPAL_REGION: the canonical region name

            This is utilized in locating the "local" endpoints of services.
        """
        session_token = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST)
        private_key = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM)
        private_key_passphrase = os.environ.get(OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM_PASSPHRASE)
        region = os.environ.get(OCI_RESOURCE_PRINCIPAL_REGION)

        return EphemeralResourcePrincipalsDelegationTokenSigner(session_token=session_token,
                                                                private_key=private_key,
                                                                private_key_passphrase=private_key_passphrase,
                                                                region=region,
                                                                delegation_token=delegation_token)
    elif rp_version == "1.1":
        resource_principal_token_endpoint = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPT_ENDPOINT)
        resource_principal_session_token_endpoint = os.environ.get(OCI_RESOURCE_PRINCIPAL_RPST_ENDPOINT)

        return ResourcePrincipalsDelegationTokenSigner(
            resource_principal_token_endpoint=resource_principal_token_endpoint,
            resource_principal_session_token_endpoint=resource_principal_session_token_endpoint,
            resource_principal_token_path_provider=resource_principal_token_path_provider,
            delegation_token=delegation_token)
    elif rp_version == "UNDEFINED":
        raise EnvironmentError("{} is not defined".format(OCI_RESOURCE_PRINCIPAL_VERSION))
    else:
        raise EnvironmentError("Unsupported {}: {}".format(OCI_RESOURCE_PRINCIPAL_VERSION, rp_version))


def get_oke_workload_identity_resource_principal_signer(service_account_token_path=None, service_account_token=None, **kwargs):
    sa_cert_path = os.environ.get(OCI_KUBERNETES_SERVICE_ACCOUNT_CERT_PATH, None)
    if sa_cert_path is None:
        sa_cert_path = DEFAULT_OCI_KUBERNETES_SERVICE_ACCOUNT_CERT_PATH

    if service_account_token is None:
        sa_token_provider = DefaultServiceAccountTokenProvider()
        if service_account_token_path is not None:
            sa_token_provider.override_sa_token_path(service_account_token_path)
    else:
        sa_token_provider = SuppliedServiceAccountTokenProvider(token_string=service_account_token)
    service_host = os.environ.get(KUBERNETES_SERVICE_HOST)
    region = os.environ.get(OCI_RESOURCE_PRINCIPAL_REGION)

    return OkeWorkloadIdentityResourcePrincipalSigner(sa_token_provider=sa_token_provider,
                                                      sa_cert_path=sa_cert_path,
                                                      service_host=service_host,
                                                      service_port=OCI_KUBERNETES_PROXYMUX_SERVICE_PORT,
                                                      region=region,
                                                      **kwargs)
