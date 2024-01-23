# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


class Request(object):

    def __init__(self,
                 method,
                 url,
                 query_params=None,
                 header_params=None,
                 body=None,
                 response_type=None,
                 enforce_content_headers=True):
        """
        :param method: HTTP method
        :param url: URL that will serve the request
        :param query_params: (optional) Query parameters in the url.
        :param header_params: (optional) Request header params.
        :param body: (optional) Request body.
        :param response_type: (optional) Response data type.
        :param enforce_content_headers: (optional) Whether content headers should be added for
            PUT and POST requests when not present.  Defaults to True.
        """

        self.method = method
        """
        The HTTP method

        :type: str
        """

        self.url = url
        """
        URL that will serve the request

        :type: str
        """

        self.query_params = query_params
        """
        Query parameters in the url

        :type: dict(str, str)
        """

        self.header_params = header_params or {}
        """
        Request header params

        :type: dict(str, str)
        """

        self.body = body
        """
        Request body
        """

        self.response_type = response_type
        """
        Response data type

        :type: str
        """

        self.enforce_content_headers = enforce_content_headers
        """
        Whether content headers should be added for PUT and POST requests when not present.  Defaults to True.

        :type: bool
        """
