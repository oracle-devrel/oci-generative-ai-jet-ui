# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

import oci._vendor.jwt as jwt
import time


class SecurityTokenContainer(object):
    DEFAULT_EXPIRY_JITTER_SECONDS = 60

    def __init__(self, session_key_supplier, security_token):
        self.security_token = security_token
        self.session_key_supplier = session_key_supplier
        self.jwt = jwt.decode(jwt=security_token, verify=False)

    def get_jwt(self):
        return self.jwt

    def valid(self):
        return not self._expired_with_jitter(0)

    def valid_with_jitter(self, jitter=DEFAULT_EXPIRY_JITTER_SECONDS):
        return not self._expired_with_jitter(jitter)

    def valid_with_half_expiration_time(self):
        valid_duration = self.jwt['exp'] - self.jwt['iat']
        return not self._expired_with_jitter(valid_duration / 2)

    def _expired_with_jitter(self, jitter):
        """
        Checks expiry with some jitter to account for clock skews on the client and also, for
        non-skewed clients, the scenario where the token was valid when we checked but became
        invalid before we sent a request (this should be rare).

        Regarding clock skew, in this context we are only worried about the scenario where the
        client's time is behind the server time as then tokens look like they will be valid for
        longer than they are and calls could fail with 401s.

        If the client's time is ahead of the server time that's not great but it would just lead
        to tokens being refreshed more often, this would not cause hard failures but could lead
        to higher perceived latency on the client

        :param int jitter:
            The amount of jitter, in seconds, to apply to the expiry time in the token
        """
        time_now = int(time.time())
        return time_now > (self.jwt['exp'] - jitter)  # The exp key which PyJWT returns is in epoch seconds
