# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .constants import HEADER_NEXT_PAGE, HEADER_REQUEST_ID


class Response(object):
    def __init__(self,
                 status,
                 headers,
                 data,
                 request):
        """
        :param status: The HTTP status code for the Response
        :param headers: The HTTP headers for the Response
        :param data: The response data.  The type of data depends on the request.
        :param request: The corresponding request for this response.
        :param next_page: (optional) The value of the `opc-next-page` response header.
        :param request_id: (optional) The ID of the request that generated this response.
        """
        self.status = status
        """
        The HTTP status code for the Response

        :type: int
        """

        self.headers = headers
        """
        The HTTP headers for the Response

        :type: :class:`requests.structures.CaseInsensitiveDict`
        """

        self.data = data
        """
        The response data.  The type of data depends on the request.
        """

        self.request = request
        """
        The corresponding request for this response.

        :type: :class:`~oci.request.Request`
        """

        self.next_page = None
        """
        The value of the `opc-next-page` response header.

        :type: str
        """

        self.request_id = None
        """
        The ID of the request that generated this response.

        :type: str"""

        if self.headers is not None:
            self.next_page = self.headers.get(HEADER_NEXT_PAGE)
            self.request_id = self.headers.get(HEADER_REQUEST_ID)

    @property
    def has_next_page(self):
        """
        Gets a value representing whether or not there is a next page of results in a list Response.

        :rtype: bool
        """
        return self.next_page is not None
