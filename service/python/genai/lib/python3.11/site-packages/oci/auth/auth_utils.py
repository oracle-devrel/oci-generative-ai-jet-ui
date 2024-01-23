# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import random
from oci._vendor import six


def get_tenancy_id_from_certificate(cert):
    if not cert:
        raise RuntimeError('A certificate must be provided')

    for name_attribute in cert.subject:
        val = name_attribute.value
        if val.startswith('opc-tenant:'):
            return val[len('opc-tenant:'):]
        if val.startswith('opc-identity:'):
            return val[len('opc-identity:'):]

    raise RuntimeError('The certificate does not contain a tenancy OCID')


def sanitize_certificate_string(cert_string):
    if six.PY3:
        string_to_replace = cert_string.decode('ascii')
    else:
        string_to_replace = cert_string

    return string_to_replace \
        .replace('-----BEGIN CERTIFICATE-----', '') \
        .replace('-----END CERTIFICATE-----', '') \
        .replace('-----BEGIN PUBLIC KEY-----', '') \
        .replace('-----END PUBLIC KEY-----', '') \
        .replace('\n', '')


def generate_opc_request_id():
    client_id = generate_unique_id()
    stack_id = generate_unique_id()
    individual_id = generate_unique_id()

    opc_request_id = "{}/{}/{}".format(client_id, stack_id, individual_id)
    return opc_request_id


def generate_unique_id():
    b = [random.randrange(256) for i in range(16)]
    hex_string = ''.join(format(x, '02x') for x in b)
    return hex_string
