# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import print_function
import os
from oci._vendor import requests
from .internal.multipart_object_assembler import MultipartObjectAssembler, DEFAULT_PARALLEL_PROCESS_COUNT
from .constants import DEFAULT_PART_SIZE, STREAMING_DEFAULT_PART_SIZE
from .internal.file_read_callback_stream import FileReadCallbackStream
from ...exceptions import MultipartUploadError


class UploadManager:
    REQUESTS_POOL_SIZE_FACTOR = 4

    def __init__(self, object_storage_client, **kwargs):
        """
        UploadManager simplifies interaction with the Object Storage service by abstracting away the method used
        to upload objects.  Depending on the configuration parameters, UploadManager may choose to do a single
        put_object request, or break up the upload into multiple parts and utilize multi-part uploads.

        An advantage of using multi-part uploads is the ability to retry individual failed parts, as well as being
        able to upload parts in parallel to reduce upload time.

        PLEASE NOTE that for oci versions < 2.23.2 and >= 2.18.0, timeout for the object storage client is overwritten to `None` for all operations which
        call object storage. For this reason, the operations are NOT thread-safe, and you should provide the
        UploadManager class with its own Object Storage client that isn't used elsewhere.
        For more information please see `Known Issues <https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/known-issues.html>`_

        :param ObjectStorageClient object_storage_client:
            A configured object storage client to use for interacting with the Object Storage service.

        :param bool allow_multipart_uploads (optional):
            Whether or not this UploadManager supports performing mulitpart uploads. Defaults to True.

        :param bool allow_parallel_uploads (optional):
            Whether or not this UploadManager supports uploading individual parts of a multipart upload in parallel.
            This setting has no effect on uploads that are performed using a single put_object call. Defaults to True.

        :param int parallel_process_count (optional):
            The number of worker processes to use in parallel for uploading individual parts of a multipart upload.
            This setting is only used if allow_parallel_uploads is set to True. Defaults to 3.
        """
        self.object_storage_client = object_storage_client
        self.allow_multipart_uploads = kwargs['allow_multipart_uploads'] if 'allow_multipart_uploads' in kwargs else True
        self.allow_parallel_uploads = kwargs['allow_parallel_uploads'] if 'allow_parallel_uploads' in kwargs else True
        self.parallel_process_count = kwargs['parallel_process_count'] if 'parallel_process_count' in kwargs else None

        UploadManager._add_adapter_to_service_client(self.object_storage_client, self.allow_parallel_uploads, self.parallel_process_count)

    def upload_stream(self,
                      namespace_name,
                      bucket_name,
                      object_name,
                      stream_ref,
                      **kwargs):
        """
        Uploads streaming data to Object Storage. If the stream is non-empty, this will always perform a multipart upload, splitting parts based
        on the part size (10 MiB if none specified). If the stream is empty, this will upload a single empty object to Object Storage.

        Stream uploads are not currently resumable.

        PLEASE NOTE that for oci versions < 2.53.1, this operation potentially causes data corruption. For more information, please see
        this `github issue <https://github.com/oracle/oci-python-sdk/issues/410>`_

        :param str namespace_name:
            The namespace containing the bucket in which to store the object.

        :param str bucket_name:
            The name of the bucket in which to store the object.

        :param str object_name:
            The name of the object in Object Storage.

        :param stream_ref:
            The stream to read data from.

        :param int part_size (optional):
            Override the default streaming part size of 10 MiB, value is in bytes.

        :param function progress_callback (optional):
            Callback function to receive the number of bytes uploaded since
            the last call to the callback function.

        :param str if_match (optional):
            The entity tag of the object to match.

        :param str if_none_match (optional):
            The entity tag of the object to avoid matching. The only valid value is ‘*’,
            which indicates that the request should fail if the object already exists.

        :param str content_type (optional):
            The content type of the object to upload.

        :param str content_language (optional):
            The content language of the object to upload.

        :param str content_encoding (optional):
            The content encoding of the object to upload.

        :param str content_disposition (optional):
            The content disposition of the object to upload.

        :param str cache_control (optional):
            The cache control for the object to upload.

        :param dict metadata (optional):
            A dictionary of string to string values to associate with the object to upload

        :param str storage_tier: (optional)
            The storage tier that the object should be stored in. If not specified, the object will be stored in
            the same storage tier as the bucket.

            Allowed values are: "Standard", "InfrequentAccess", "Archive"

        :return:
            The response from multipart commit operation or the put operation.  In both cases this will be a :class:`~oci.response.Response` object with data of type None.
            For a multipart upload (non-empty stream data) the :class:`~oci.response.Response` will contain the :code:`opc-multipart-md5` header and for a non-multipart upload
            (empty stream data) it will contain the :code:`opc-content-md5 header`.
        :rtype: :class:`~oci.response.Response`
        """

        if 'part_size' not in kwargs:
            kwargs['part_size'] = STREAMING_DEFAULT_PART_SIZE

        kwargs['allow_parallel_uploads'] = self.allow_parallel_uploads
        if self.parallel_process_count is not None:
            kwargs['parallel_process_count'] = self.parallel_process_count

        ma = MultipartObjectAssembler(
            self.object_storage_client,
            namespace_name,
            bucket_name,
            object_name,
            **kwargs
        )

        upload_kwargs = {}
        if 'progress_callback' in kwargs:
            upload_kwargs['progress_callback'] = kwargs['progress_callback']

        ma.new_upload()

        try:
            ma.upload_stream(stream_ref, **upload_kwargs)
        except MultipartUploadError:
            # Since the stream upload is not resumable, make an effort to clean up after ourselves before
            # failing out
            ma.abort()
            raise

        # It is possible we did not upload any parts (e.g. if the stream was empty). If we did
        # upload parts then commit the upload, otherwise abort the upload and put an empty object
        # into Object Storage to reflect what the customer intended.
        if len(ma.manifest['parts']) > 0:
            response = ma.commit()
        else:
            ma.abort()
            copy_kwargs = kwargs.copy()
            # put_object expects 'opc_meta' not metadata
            if 'metadata' in copy_kwargs:
                copy_kwargs['opc_meta'] = copy_kwargs['metadata']
                copy_kwargs.pop('metadata')

            # These parameters are not valid for just putting the object, so discard them
            copy_kwargs.pop('progress_callback', None)
            copy_kwargs.pop('part_size', None)
            copy_kwargs.pop('allow_parallel_uploads', None)
            copy_kwargs.pop('parallel_process_count', None)

            return self.object_storage_client.put_object(namespace_name, bucket_name, object_name, b'', **copy_kwargs)

        return response

    def upload_file(self,
                    namespace_name,
                    bucket_name,
                    object_name,
                    file_path,
                    **kwargs):
        """
        Uploads an object to Object Storage. Depending on the options provided and the
        size of the object, the object may be uploaded in multiple parts.

        :param str namespace_name:
            The namespace containing the bucket in which to store the object.

        :param str bucket_name:
            The name of the bucket in which to store the object.

        :param str object_name:
            The name of the object in Object Storage.

        :param file_path:
            The path to the file to upload.

        :param int part_size (optional):
            Override the default part size of 128 MiB, value is in bytes.

        :param function progress_callback (optional):
            Callback function to receive the number of bytes uploaded since
            the last call to the callback function.

        :param str if_match (optional):
            The entity tag of the object to match.

        :param str if_none_match (optional):
            The entity tag of the object to avoid matching. The only valid value is ‘*’,
            which indicates that the request should fail if the object already exists.

        :param str content_md5: (optional)
            The base-64 encoded MD5 hash of the body. This parameter is only used if the object is uploaded in a single part.

        :param str content_type (optional):
            The content type of the object to upload.

        :param str content_language (optional):
            The content language of the object to upload.

        :param str content_encoding (optional):
            The content encoding of the object to upload.

        :param str content_disposition (optional):
            The content disposition of the object to upload.

        :param str cache_control (optional):
            The cache control for the object to upload.

        :param dict metadata (optional):
            A dictionary of string to string values to associate with the object to upload

        :param str storage_tier: (optional)
            The storage tier that the object should be stored in. If not specified, the object will be stored in
            the same storage tier as the bucket.

            Allowed values are: "Standard", "InfrequentAccess", "Archive"

        :return:
            The response from multipart commit operation or the put operation.  In both cases this will be a :class:`~oci.response.Response` object with data of type None.
            For a multipart upload the :class:`~oci.response.Response` will contain the :code:`opc-multipart-md5` header and for a non-multipart upload
            it will contain the :code:`opc-content-md5 header`.
        :rtype: :class:`~oci.response.Response`
        """

        part_size = DEFAULT_PART_SIZE
        if 'part_size' in kwargs:
            part_size = kwargs['part_size']
            kwargs.pop('part_size')

        with open(file_path, 'rb') as file_object:
            file_size = os.fstat(file_object.fileno()).st_size
            if not self.allow_multipart_uploads or not UploadManager._use_multipart(file_size, part_size=part_size):
                return self._upload_singlepart(namespace_name, bucket_name, object_name, file_path, **kwargs)
            else:
                if 'content_md5' in kwargs:
                    kwargs.pop('content_md5')

                kwargs['part_size'] = part_size
                kwargs['allow_parallel_uploads'] = self.allow_parallel_uploads
                if self.parallel_process_count is not None:
                    kwargs['parallel_process_count'] = self.parallel_process_count

                ma = MultipartObjectAssembler(self.object_storage_client,
                                              namespace_name,
                                              bucket_name,
                                              object_name,
                                              **kwargs)

                upload_kwargs = {}
                if 'progress_callback' in kwargs:
                    upload_kwargs['progress_callback'] = kwargs['progress_callback']

                ma.new_upload()
                ma.add_parts_from_file(file_path)
                ma.upload(**upload_kwargs)
                response = ma.commit()

                return response

    def resume_upload_file(self,
                           namespace_name,
                           bucket_name,
                           object_name,
                           file_path,
                           upload_id,
                           **kwargs):

        """
        Resume a multipart upload.

        :param str namespace_name:
            The namespace containing the bucket and multipart upload to resume.

        :param str bucket_name:
            The name of the bucket that contains the multipart upload to resume.

        :param str object_name:
            The name of the object in Object Storage.

        :param file_path:
            The path to the file to upload.

        :param str upload_id:
            The upload id for the multipart upload to resume.

        :param int part_size (optional):
            Part size, in bytes, to use when resuming the transfer. The
            default is 128 mebibytes.  If this value is supplied, it must
            be the same value as the one used when the original upload
            was started.

        :param function progress_callback (optional):
            Callback function to receive the number of bytes uploaded since
            the last call to the callback function.

        :return:
            The response from the multipart commit operation. This will be a :class:`~oci.response.Response` object with data of type None
        :rtype: :class:`~oci.response.Response`
        """

        resume_kwargs = {}
        if 'progress_callback' in kwargs:
            resume_kwargs['progress_callback'] = kwargs['progress_callback']
            kwargs.pop('progress_callback')

        kwargs['allow_parallel_uploads'] = self.allow_parallel_uploads
        if self.parallel_process_count is not None:
            kwargs['parallel_process_count'] = self.parallel_process_count

        ma = MultipartObjectAssembler(self.object_storage_client,
                                      namespace_name,
                                      bucket_name,
                                      object_name,
                                      **kwargs)
        ma.add_parts_from_file(file_path)
        ma.resume(upload_id=upload_id, **resume_kwargs)
        response = ma.commit()

        return response

    def _upload_singlepart(self,
                           namespace_name,
                           bucket_name,
                           object_name,
                           file_path,
                           **kwargs):

        # put_object expects 'opc_meta' not metadata
        if 'metadata' in kwargs:
            kwargs['opc_meta'] = kwargs['metadata']
            kwargs.pop('metadata')

        # remove unrecognized kwargs for put_object
        progress_callback = None
        if 'progress_callback' in kwargs:
            progress_callback = kwargs['progress_callback']
            kwargs.pop('progress_callback')

        with open(file_path, 'rb') as file_object:
            # progress_callback is not supported for files of zero bytes
            # FileReadCallbackStream will not be handled properly by requests in this case
            file_size = os.fstat(file_object.fileno()).st_size
            if file_size != 0 and progress_callback:
                wrapped_file = FileReadCallbackStream(file_object,
                                                      lambda bytes_read: progress_callback(bytes_read))

                response = self.object_storage_client.put_object(namespace_name,
                                                                 bucket_name,
                                                                 object_name,
                                                                 wrapped_file,
                                                                 **kwargs)
            else:
                response = self.object_storage_client.put_object(namespace_name,
                                                                 bucket_name,
                                                                 object_name,
                                                                 file_object,
                                                                 **kwargs)
        return response

    @staticmethod
    def _add_adapter_to_service_client(object_storage_client, allow_parallel_uploads, parallel_process_count):
        # No need to mount with a larger pool size if we are not running multiple threads
        if not allow_parallel_uploads or not parallel_process_count:
            return

        endpoint = object_storage_client.base_client.endpoint
        mount_protocol = 'https://'
        if endpoint.startswith('http://'):
            mount_protocol = 'http://'

        parallel_processes = DEFAULT_PARALLEL_PROCESS_COUNT
        if parallel_process_count is not None:
            parallel_processes = parallel_process_count

        target_pool_size = UploadManager.REQUESTS_POOL_SIZE_FACTOR * parallel_processes
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=target_pool_size)

        if mount_protocol in object_storage_client.base_client.session.adapters:
            # If someone has already mounted and it's large enough, don't mount over the top
            if object_storage_client.base_client.session.adapters[mount_protocol]._pool_maxsize >= target_pool_size:
                return

        object_storage_client.base_client.session.mount(mount_protocol, adapter)

    @staticmethod
    def _use_multipart(content_length, part_size=DEFAULT_PART_SIZE):
        return part_size < content_length
