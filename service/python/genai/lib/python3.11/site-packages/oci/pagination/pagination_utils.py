# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from .. import dns, object_storage
from .. import retry
from ..response import Response


def list_call_get_up_to_limit(list_func_ref, record_limit, page_size, *list_func_args, **list_func_kwargs):
    """
    Calls a list operation and automatically fetches more data from the service (automatically following pagination tokens) until
    the desired number of records is reached (or there are no more records left, if the total number of records is less than
    the desired number of records). Apart from the formally listed parameters for this function, any additional
    positional (``*list_func_args``) and keyword (``**list_func_kwargs``) arguments will be passed to the list operation.

    Results are eagerly loaded and the response returned by this function will contain all the data up to the desired
    number of records (or there are no more records left, whichever is first). If you wish to lazy load results, then use
    the version of this method which produces a generator: :py:func:`~oci.pagination.list_call_get_up_to_limit_generator`

    :param function list_func_ref:
        A reference to the list operation which we will call

    :param int record_limit:
        The maximum number of records to fetch. We may fetch less records than this if the total number of records is less than
        this value. If a record_limit is not provided then we will only fetch a single page of data

    :param int page_size:
        The number of records to retrieve per list operation call

    :return:
        A :class:`~oci.response.Response` whose data attribute contains all the records we retrieved. The other attributes of the
        :class:`~oci.response.Response` object will be sourced from the last response we received from calling the list operation on the service.
    :rtype: :class:`~oci.response.Response`
    """
    call_result = None
    aggregated_results = []
    is_dns_record_collection = False
    dns_record_collection_class = None
    is_list_objects_response = False
    list_objects_prefixes = set()
    for response in list_call_get_up_to_limit_generator(list_func_ref, record_limit, page_size, 'response', *list_func_args, **list_func_kwargs):
        call_result = response

        if isinstance(call_result.data, dns.models.RecordCollection) or isinstance(call_result.data, dns.models.RRSet):
            is_dns_record_collection = True
            dns_record_collection_class = call_result.data.__class__
            aggregated_results.extend(call_result.data.items)
        elif isinstance(call_result.data, object_storage.models.ListObjects):
            is_list_objects_response = True
            aggregated_results.extend(call_result.data.objects)
            if call_result.data.prefixes:
                list_objects_prefixes.update(call_result.data.prefixes)
        else:
            aggregated_results.extend(call_result.data) if isinstance(call_result.data, list) \
                else aggregated_results.extend(call_result.data.items)

    if is_dns_record_collection:
        final_response = Response(
            call_result.status,
            call_result.headers,
            dns_record_collection_class(items=aggregated_results),
            call_result.request
        )
    elif is_list_objects_response:
        final_response = Response(
            call_result.status,
            call_result.headers,
            object_storage.models.ListObjects(
                objects=aggregated_results,
                prefixes=list(list_objects_prefixes)
            ),
            call_result.request
        )
    else:
        final_response = Response(call_result.status, call_result.headers, aggregated_results, call_result.request)
    return final_response


def list_call_get_up_to_limit_generator(list_func_ref, record_limit, page_size, yield_mode, *list_func_args, **list_func_kwargs):
    """
    Calls a list operation and automatically fetches more data from the service (automatically following pagination tokens) until
    the desired number of records is reached (or there are no more records left, if the total number of records is less than
    the desired number of records). Apart from the formally listed parameters for this function, any additional
    positional (``*list_func_args``) and keyword (``**list_func_kwargs``) arguments will be passed to the list operation.

    This function produces a generator and lazily loads results. That is, service calls will only be made to fetch more data
    when needed as we iterate through results produced by the generator; this contrasts with the eagarily loaded
    :py:func:`~oci.pagination.list_call_get_up_to_limit` function, which makes all the required service calls when it is called.

    The generator also supports vending two types of objects - either the raw responses received from calling the list operation,
    or the individual model objects which are contained within the response's ``data`` attribute (which should be
    a list of model objects).

    :param function list_func_ref:
        A reference to the list operation which we will call

    :param int record_limit:
        The maximum number of records to fetch. We may fetch less records than this if the total number of records is less than
        this value. If a record_limit is not provided then we will only fetch a single page of data

    :param int page_size:
        The number of records to retrieve per list operation call

    :param str yield_mode:
        Either ``response`` or ``record``. This will control whether the generator returned by this function yields
        either :class:`~oci.response.Response` objects (if the value is ``response``), or whether it yields the
        individual model objects which are contained within the response's ``data`` attribute (which should
        be a list of model objects)

    :return:
        A generator that, depending on the ``yield_mode``, will yield either :class:`~oci.response.Response` objects
        or the individual model objects which are contained within the response's ``data`` attribute (which should
        be a list of model objects)
    """
    if not record_limit and not page_size:
        raise ValueError('You must provide one, or both, of a record_limit and page_size')

    # If no limit was provided, make a single call
    if record_limit is None:
        list_func_kwargs['limit'] = page_size
        single_call_result = retry.DEFAULT_RETRY_STRATEGY.make_retrying_call(list_func_ref, *list_func_args, **list_func_kwargs)

        if yield_mode == 'response':
            yield single_call_result
        else:
            items_to_yield = []
            if isinstance(single_call_result.data, dns.models.RecordCollection) or isinstance(single_call_result.data, dns.models.RRSet):
                items_to_yield = single_call_result.data.items
            elif isinstance(single_call_result.data, object_storage.models.ListObjects):
                items_to_yield = single_call_result.data.objects
            else:
                items_to_yield = single_call_result.data

            for item in items_to_yield:
                yield item

        return  # This will terminate after we yield everything we can from the single result

    # If we have a limit, make calls until we get that amount of data
    keep_paginating = True
    remaining_items_to_fetch = record_limit
    call_result = None
    while keep_paginating and remaining_items_to_fetch > 0:
        list_func_kwargs['limit'] = min(page_size, remaining_items_to_fetch)

        call_result = retry.DEFAULT_RETRY_STRATEGY.make_retrying_call(list_func_ref, *list_func_args, **list_func_kwargs)
        if yield_mode == 'response':
            yield call_result
        else:
            items_to_yield = []
            if isinstance(call_result.data, dns.models.RecordCollection) or isinstance(call_result.data, dns.models.RRSet):
                items_to_yield = call_result.data.items
            elif isinstance(call_result.data, object_storage.models.ListObjects):
                items_to_yield = call_result.data.objects
            else:
                items_to_yield = call_result.data if isinstance(call_result.data, list) else call_result.data.items

            for item in items_to_yield:
                yield item

        if isinstance(call_result.data, dns.models.RecordCollection) or isinstance(call_result.data, dns.models.RRSet):
            remaining_items_to_fetch -= len(call_result.data.items)
        elif isinstance(call_result.data, object_storage.models.ListObjects):
            remaining_items_to_fetch -= len(call_result.data.objects)
        else:
            remaining_items_to_fetch -= len(call_result.data) if isinstance(call_result.data, list) else len(call_result.data.items)

        if isinstance(call_result.data, object_storage.models.ListObjects):
            if call_result.data.next_start_with is not None:
                list_func_kwargs['start'] = call_result.data.next_start_with
            keep_paginating = (call_result.data.next_start_with is not None)
        else:
            if call_result.next_page is not None:
                list_func_kwargs['page'] = call_result.next_page

            keep_paginating = call_result.has_next_page


def list_call_get_all_results(list_func_ref, *list_func_args, **list_func_kwargs):
    """
    Calls a list operation and automatically fetches more data from the service (automatically following pagination tokens) until
    the no more records are available. Apart from the formally listed parameters for this function, any additional
    positional (``*list_func_args``) and keyword (``**list_func_kwargs``) arguments will be passed to the list operation.

    Results are eagerly loaded and the response returned by this function will contain all the available data. If you wish
    to lazy load results, then use the version of this method which produces a generator:
    :py:func:`~oci.pagination.list_call_get_all_results_generator`

    :param function list_func_ref:
        A reference to the list operation which we will call

    :return:
        A :class:`~oci.response.Response` whose data attribute contains all the records we retrieved. The other attributes of the
        :class:`~oci.response.Response` object will be sourced from the last response we received from calling the list operation on the service.
    :rtype: :class:`~oci.response.Response`
    """

    aggregated_results = []
    call_result = None
    is_dns_record_collection = False
    dns_record_collection_class = None
    is_list_objects_response = False
    list_objects_prefixes = set()
    for response in list_call_get_all_results_generator(list_func_ref, 'response', *list_func_args, **list_func_kwargs):
        call_result = response
        if isinstance(call_result.data, dns.models.RecordCollection) or isinstance(call_result.data, dns.models.RRSet):
            is_dns_record_collection = True
            dns_record_collection_class = call_result.data.__class__
            aggregated_results.extend(call_result.data.items)
        elif isinstance(call_result.data, object_storage.models.ListObjects):
            is_list_objects_response = True
            aggregated_results.extend(call_result.data.objects)
            if call_result.data.prefixes:
                list_objects_prefixes.update(call_result.data.prefixes)
        else:
            aggregated_results.extend(call_result.data) if isinstance(call_result.data, list) \
                else aggregated_results.extend(call_result.data.items)

    if is_dns_record_collection:
        final_response = Response(
            call_result.status,
            call_result.headers,
            dns_record_collection_class(items=aggregated_results),
            call_result.request
        )
    elif is_list_objects_response:
        final_response = Response(
            call_result.status,
            call_result.headers,
            object_storage.models.ListObjects(
                objects=aggregated_results,
                prefixes=list(list_objects_prefixes)
            ),
            call_result.request
        )
    else:
        final_response = Response(call_result.status, call_result.headers, aggregated_results, call_result.request)
    return final_response


def list_call_get_all_results_generator(list_func_ref, yield_mode, *list_func_args, **list_func_kwargs):
    """
    Calls a list operation and automatically fetches more data from the service (automatically following pagination tokens) until
    the no more records are available. Apart from the formally listed parameters for this function, any additional
    positional (``*list_func_args``) and keyword (``**list_func_kwargs``) arguments will be passed to the list operation.

    This function produces a generator and lazily loads results. That is, service calls will only be made to fetch more data
    when needed as we iterate through results produced by the generator; this contrasts with the eagarily loaded
    :py:func:`~oci.pagination.list_call_get_all_results` function, which makes all the required service calls when it is called.

    The generator also supports vending two types of objects - either the raw responses received from calling the list operation,
    or the individual model objects which are contained within the response's ``data`` attribute (which should be
    a list of model objects).

    :param function list_func_ref:
        A reference to the list operation which we will call

    :param str yield_mode:
        Either ``response`` or ``record``. This will control whether the generator returned by this function yields
        either :class:`~oci.response.Response` objects (if the value is ``response``), or whether it yields the
        individual model objects which are contained within the response's ``data`` attribute (which should
        be a list of model objects)

    :return:
        A generator that, depending on the ``yield_mode``, will yield either :class:`~oci.response.Response` objects
        or the individual model objects which are contained within the response's ``data`` attribute (which should
        be a list of model objects)
    """
    keep_paginating = True
    call_result = None

    while keep_paginating:
        call_result = retry.DEFAULT_RETRY_STRATEGY.make_retrying_call(list_func_ref, *list_func_args, **list_func_kwargs)
        if yield_mode == 'response':
            yield call_result
        else:
            items_to_yield = []
            if isinstance(call_result.data, dns.models.RecordCollection) or isinstance(call_result.data, dns.models.RRSet):
                items_to_yield = call_result.data.items
            elif isinstance(call_result.data, object_storage.models.ListObjects):
                items_to_yield = call_result.data.objects
            else:
                items_to_yield = call_result.data if isinstance(call_result.data, list) else call_result.data.items

            for item in items_to_yield:
                yield item

        if isinstance(call_result.data, object_storage.models.ListObjects):
            if call_result.data.next_start_with is not None:
                list_func_kwargs['start'] = call_result.data.next_start_with
            keep_paginating = (call_result.data.next_start_with is not None)
        else:
            if call_result.next_page is not None:
                list_func_kwargs['page'] = call_result.next_page

            keep_paginating = call_result.has_next_page
