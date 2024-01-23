# coding: utf-8
# Modified Work: Copyright (c) 2018, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.
# Original Work: Copyright (c) 2015 José Padilla

# -*- coding: utf-8 -*-
# flake8: noqa

"""
JSON Web Token implementation

Minimum implementation based on this spec:
http://self-issued.info/docs/draft-jones-json-web-token-01.html
"""


__title__ = 'pyjwt'
__version__ = '1.7.1'
__author__ = 'José Padilla'
__license__ = 'MIT'
__copyright__ = 'Copyright 2015-2018 José Padilla'


from .api_jwt import (
    encode, decode, register_algorithm, unregister_algorithm,
    get_unverified_header, PyJWT
)
from .api_jws import PyJWS
from .exceptions import (
    InvalidTokenError, DecodeError, InvalidAlgorithmError,
    InvalidAudienceError, ExpiredSignatureError, ImmatureSignatureError,
    InvalidIssuedAtError, InvalidIssuerError, ExpiredSignature,
    InvalidAudience, InvalidIssuer, MissingRequiredClaimError,
    InvalidSignatureError,
    PyJWTError,
)
