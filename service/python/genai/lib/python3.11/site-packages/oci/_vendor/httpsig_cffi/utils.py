# coding: utf-8
# Modified Work: Copyright (c) 2018, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.
# Original Work: Copyright (c) 2014 Adam Knight
# Original Work: Copyright (c) 2012 Adam T. Lindsay (original author)

import re
import struct
import hashlib
import base64
from oci._vendor import six

try:
    # Python 3
    from urllib.request import parse_http_list
except ImportError:
    # Python 2
    from urllib2 import parse_http_list

from cryptography.hazmat.primitives.hashes import SHA1, SHA256, SHA512

ALGORITHMS = frozenset(['rsa-sha1', 'rsa-sha256', 'rsa-sha512', 'hmac-sha1', 'hmac-sha256', 'hmac-sha512'])
HASHES = {'sha1': SHA1, 'sha256': SHA256, 'sha512': SHA512}


class HttpSigException(Exception):
    pass


def generate_message(required_headers, headers, host=None, method=None, path=None):
    headers = CaseInsensitiveDict(headers)

    if not required_headers:
        required_headers = ['date']

    signable_list = []
    for h in required_headers:
        h = h.lower()
        if h == '(request-target)':
            if not method or not path:
                raise Exception('method and path arguments required when using "(request-target)"')
            signable_list.append('%s: %s %s' % (h, method.lower(), path))

        elif h == 'host':
            # 'host' special case due to requests lib restrictions
            # 'host' is not available when adding auth so must use a param
            # if no param used, defaults back to the 'host' header
            if not host:
                if 'host' in headers:
                    host = headers[h]
                else:
                    raise Exception('missing required header "%s"' % (h))
            signable_list.append('%s: %s' % (h, host))
        else:
            if h not in headers:
                raise Exception('missing required header "%s"' % (h))

            signable_list.append('%s: %s' % (h, headers[h]))

    signable = '\n'.join(signable_list).encode("ascii")
    return signable


def parse_authorization_header(header):
    if not isinstance(header, six.string_types):
        header = header.decode("ascii")  # HTTP headers cannot be Unicode.

    auth = header.split(" ", 1)
    if len(auth) > 2:
        raise ValueError('Invalid authorization header. (eg. Method key1=value1,key2="value, \"2\"")')

    # Split up any args into a dictionary.
    values = {}
    if len(auth) == 2:
        auth_value = auth[1]
        if auth_value and len(auth_value):
            # This is tricky string magic.  Let urllib do it.
            fields = parse_http_list(auth_value)

            for item in fields:
                # Only include keypairs.
                if '=' in item:
                    # Split on the first '=' only.
                    key, value = item.split('=', 1)
                    if not (len(key) and len(value)):
                        continue

                    # Unquote values, if quoted.
                    if value[0] == '"':
                        value = value[1:-1]

                    values[key] = value

    # ("Signature", {"headers": "date", "algorithm": "hmac-sha256", ... })
    return (auth[0], CaseInsensitiveDict(values))


def build_signature_template(key_id, algorithm, headers):
    """
    Build the Signature template for use with the Authorization header.

    key_id is the mandatory label indicating to the server which secret to use
    algorithm is one of the six specified algorithms
    headers is a list of http headers to be included in the signing string.

    The signature must be interpolated into the template to get the final Authorization header value.
    """
    param_map = {'keyId': key_id,
                 'algorithm': algorithm,
                 'signature': '%s'}
    if headers:
        headers = [h.lower() for h in headers]
        param_map['headers'] = ' '.join(headers)
    kv = map('{0[0]}="{0[1]}"'.format, param_map.items())
    kv_string = ','.join(kv)
    sig_string = 'Signature {0}'.format(kv_string)
    return sig_string


def lkv(d):
    parts = []
    while d:
            len = struct.unpack('>I', d[:4])[0]
            bits = d[4:(len + 4)]
            parts.append(bits)
            d = d[(len + 4):]
    return parts


def sig(d):
    return lkv(d)[1]


def is_rsa(keyobj):
    return lkv(keyobj.blob)[0] == "ssh-rsa"


# based on http://stackoverflow.com/a/2082169/151401
class CaseInsensitiveDict(dict):
    def __init__(self, d=None, **kwargs):
        super(CaseInsensitiveDict, self).__init__(**kwargs)
        if d:
            self.update((k.lower(), v) for k, v in six.iteritems(d))

    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

    def __contains__(self, key):
        return super(CaseInsensitiveDict, self).__contains__(key.lower())


# currently busted...
def get_fingerprint(key):
    """
    Takes an ssh public key and generates the fingerprint.

    See: http://tools.ietf.org/html/rfc4716 for more info
    """
    if key.startswith('ssh-rsa'):
        key = key.split(' ')[1]
    else:
        regex = r'\-{4,5}[\w|| ]+\-{4,5}'
        key = re.split(regex, key)[1]

    key = key.replace('\n', '')
    key = key.strip().encode('ascii')
    key = base64.b64decode(key)
    fp_plain = hashlib.md5(key).hexdigest()
    return ':'.join(a + b for a, b in zip(fp_plain[::2], fp_plain[1::2]))
