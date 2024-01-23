# coding: utf-8
# Modified Work: Copyright (c) 2018, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.
# Original Work: Copyright (c) 2014 Adam Knight
# Original Work: Copyright (c) 2012 Adam T. Lindsay (original author)

from oci._vendor.requests.auth import AuthBase
try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

from .sign import HeaderSigner


class HTTPSignatureAuth(AuthBase):
    '''
    Sign a request using the http-signature scheme.
    https://github.com/joyent/node-http-signature/blob/master/http_signing.md

    key_id is the mandatory label indicating to the server which secret to use
    secret is the filename of a pem file in the case of rsa, a password string in the case of an hmac algorithm
    algorithm is one of the six specified algorithms
    headers is a list of http headers to be included in the signing string, defaulting to "Date" alone.
    '''
    def __init__(self, key_id='', secret='', algorithm=None, headers=None):
        headers = headers or []
        self.header_signer = HeaderSigner(
            key_id=key_id,
            secret=secret,
            algorithm=algorithm,
            headers=headers
        )
        self.uses_host = 'host' in [h.lower() for h in headers]

    def __call__(self, r):
        headers = self.header_signer.sign(
            r.headers,
            # 'Host' header unavailable in request object at this point
            # if 'host' header is needed, extract it from the url
            host=urlparse(r.url).netloc if self.uses_host else None,
            method=r.method,
            path=r.path_url
        )
        r.headers.update(headers)
        return r
